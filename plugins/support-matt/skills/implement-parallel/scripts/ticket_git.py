#!/usr/bin/env python3
"""把一張票併入整合分支，並把驗收核對寫回 ticket。

merge      以 git merge --squash 把票分支併成整合分支上的一個票級 commit。
           預設只預演：檢查前提與衝突、回報會進來的檔案，不寫入。加上 --apply 才提交。
writeback  依票級 agent 產出的核對紀錄勾選 ticket 的驗收條件，並寫入或就地更新「驗收核對」段落。

stdout 只印一行 JSON。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

COMMIT_SUBJECT = re.compile(r"^(feat|fix|refactor|chore|test): \S")
CHECKBOX = re.compile(r"^- \[[ xX]\] ")
RECORD_HEADING = "## 驗收核對"
CHECKED_PREFIX = "勾選："


class Stop(Exception):
    def __init__(self, status, **fields):
        super().__init__(status)
        self.fields = {"status": status, **fields}


def git(cwd, *args, check=True):
    result = subprocess.run(
        ["git", "-C", cwd, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        raise Stop("git_failed", command="git " + " ".join(args), stderr=result.stderr.strip())
    return result


def lines_of(text):
    return [line for line in text.splitlines() if line.strip()]


def read_message(path):
    with open(path, encoding="utf-8-sig") as handle:
        message = handle.read().replace("\r\n", "\n").strip()
    if not message:
        raise Stop("bad_message", message="commit message 是空的")
    subject = message.splitlines()[0]
    if not COMMIT_SUBJECT.match(subject):
        raise Stop("bad_message", message="標題須以 feat／fix／refactor／chore／test 加上「: 」開頭", subject=subject)
    return message, subject


def merge(args):
    message, subject = read_message(args.message_file)

    current = git(args.repo, "branch", "--show-current").stdout.strip()
    if current != args.integration:
        raise Stop("wrong_branch", message=f"主 checkout 目前在 {current or '(detached)'}，不是整合分支 {args.integration}")
    tracked_changes = lines_of(git(args.repo, "status", "--porcelain", "--untracked-files=no").stdout)
    if tracked_changes:
        raise Stop("dirty_repo", message="主 checkout 有未提交的已追蹤檔案變更", files=tracked_changes)
    ticket_changes = lines_of(git(args.worktree, "status", "--porcelain").stdout)
    if ticket_changes:
        raise Stop("uncommitted_ticket_changes", message="票的 worktree 還有未提交的變更", files=ticket_changes)

    ahead = int(git(args.repo, "rev-list", "--count", f"{args.integration}..{args.ticket_branch}").stdout.strip())
    if ahead == 0:
        raise Stop("nothing_to_merge", message=f"{args.ticket_branch} 沒有領先 {args.integration} 的 commit")

    probe = git(args.repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", args.integration, args.ticket_branch, check=False)
    probe_lines = lines_of(probe.stdout)
    if probe.returncode == 1:
        raise Stop("conflict", message="與目前的整合分支衝突", files=probe_lines[1:])
    if probe.returncode != 0:
        raise Stop("git_failed", command="git merge-tree", stderr=probe.stderr.strip())
    merged_tree = probe_lines[0]
    if merged_tree == git(args.repo, "rev-parse", f"{args.integration}^{{tree}}").stdout.strip():
        raise Stop("empty_diff", message="併入後整合分支沒有任何變化")
    stat = git(args.repo, "diff", "--stat", args.integration, merged_tree).stdout.rstrip()

    if not args.apply:
        return {"status": "preview", "subject": subject, "stat": stat}

    squash = git(args.repo, "merge", "--squash", args.ticket_branch, check=False)
    if squash.returncode != 0:
        raise Stop("merge_failed", message="git merge --squash 失敗，主 checkout 可能留有未完成的合併，請檢查後再處理", stderr=squash.stderr.strip() or squash.stdout.strip())
    staged = git(args.repo, "diff", "--cached", "--stat").stdout.rstrip()

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as handle:
        handle.write(message + "\n")
        message_path = handle.name
    try:
        # whitespace 只整理空白，不像預設的 strip 會把 # 開頭的行當註解刪掉。
        git(args.repo, "commit", "--cleanup=whitespace", "-F", message_path)
    finally:
        os.remove(message_path)

    commit = git(args.repo, "rev-parse", "HEAD").stdout.strip()
    committed_tree = git(args.repo, "rev-parse", "HEAD^{tree}").stdout.strip()
    if committed_tree != merged_tree:
        raise Stop("tree_mismatch", message="提交內容與預演的合併結果不同，請檢查", commit=commit)
    return {"status": "merged", "commit": commit, "subject": subject, "staged": staged}


def read_record(path):
    with open(path, encoding="utf-8-sig") as handle:
        lines = handle.read().replace("\r\n", "\n").strip().split("\n")
    if not lines[0].startswith(CHECKED_PREFIX):
        raise Stop("bad_record", message=f"核對紀錄第一行須為「{CHECKED_PREFIX}1, 2, 4」或「{CHECKED_PREFIX}無」")
    value = lines[0][len(CHECKED_PREFIX):].strip()
    checked = set()
    if value != "無":
        for item in re.split(r"[,、，\s]+", value):
            if not item.isdigit():
                raise Stop("bad_record", message=f"勾選項目須為數字：{item}")
            checked.add(int(item))
    section = [line.rstrip() for line in lines[1:]]
    while section and not section[0]:
        section.pop(0)
    if not section or not section[0].startswith(RECORD_HEADING):
        raise Stop("bad_record", message=f"勾選行之後須接「{RECORD_HEADING}（YYYY-MM-DD）」段落")
    return checked, section


def find_section(lines):
    """回傳既有「驗收核對」段落的 (起, 迄)；沒有時回傳 None。"""
    for start, line in enumerate(lines):
        if line.startswith(RECORD_HEADING):
            end = start + 1
            while end < len(lines) and not lines[end].startswith("## "):
                end += 1
            return start, end
    return None


def writeback(args):
    checked, section = read_record(args.record)
    commit = git(args.repo, "log", "-1", "--format=%h %s", args.commit).stdout.strip()

    with open(args.ticket, "rb") as handle:
        raw = handle.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")

    existing = find_section(lines)
    if existing:
        start, end = existing
        lines = lines[:start] + lines[end:]
    else:
        start = None

    boxes = [index for index, line in enumerate(lines) if CHECKBOX.match(line)]
    out_of_range = sorted(number for number in checked if not 1 <= number <= len(boxes))
    if out_of_range:
        raise Stop("bad_record", message=f"ticket 只有 {len(boxes)} 條頂層驗收條件", out_of_range=out_of_range)
    for number, index in enumerate(boxes, start=1):
        mark = "x" if number in checked else " "
        lines[index] = f"- [{mark}] " + lines[index][6:]

    block = section + ["", f"交付 commit：`{commit}`", ""]
    if start is None:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += [""] + block
    else:
        lines[start:start] = block

    content = newline.join(lines).rstrip("\r\n") + newline
    with open(args.ticket, "wb") as handle:
        handle.write((b"\xef\xbb\xbf" if bom else b"") + content.encode("utf-8"))
    return {
        "status": "written",
        "ticket": args.ticket,
        "checked": sorted(checked),
        "criteria": len(boxes),
        "commit": commit,
        "replaced": existing is not None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    merge_parser = sub.add_parser("merge", help="把票分支 squash 併入整合分支")
    merge_parser.add_argument("--repo", required=True, help="主 checkout 路徑，目前須在整合分支")
    merge_parser.add_argument("--integration", required=True, help="整合分支名稱")
    merge_parser.add_argument("--ticket-branch", required=True, help="票分支名稱")
    merge_parser.add_argument("--worktree", required=True, help="票的 worktree 路徑，須已無未提交變更")
    merge_parser.add_argument("--message-file", required=True, help="使用者核准的完整 commit message")
    merge_parser.add_argument("--apply", action="store_true", help="實際提交；省略時只預演")

    writeback_parser = sub.add_parser("writeback", help="把驗收核對寫回 ticket")
    writeback_parser.add_argument("--repo", required=True, help="主 checkout 路徑")
    writeback_parser.add_argument("--ticket", required=True, help="主 checkout 內的 ticket 檔案")
    writeback_parser.add_argument("--record", required=True, help="票級 agent 產出的核對紀錄")
    writeback_parser.add_argument("--commit", required=True, help="整合分支上的票級 commit")

    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        result = merge(args) if args.command == "merge" else writeback(args)
        code = 0
    except Stop as stop:
        result, code = stop.fields, 1
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
