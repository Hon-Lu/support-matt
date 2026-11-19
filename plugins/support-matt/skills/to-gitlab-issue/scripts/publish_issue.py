#!/usr/bin/env python3
"""把 feature 目錄的文件發布到 GitLab Issue。

預設只做預演：備份現況、組好內容、回報會發生什麼，不寫入 GitLab。
加上 --apply 才會寫入。stdout 只印一行 JSON，不含文件內文。
"""
import argparse
import difflib
import glob
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse

MAX_BODY_CHARS = 1_000_000
TICKETS_HEADING = "# 開發紀錄（TICKETS）"
MAP_HEADING_PREFIX = "# 驗收盤點"
# brief 與 draft 還在變動，不該蓋掉主內文，所以只發布各自的完成狀態。
DESCRIPTION_SOURCES = (("feature-doc.md", "final"), ("handoff-doc.md", "ready"))
URL_PATTERN = re.compile(r"^https?://([^/]+)/(.+?)/-/(?:issues|work_items)/(\d+)/?(?:[?#].*)?$")

# 只比對「看起來真的帶值」的寫法，避免把「帳號沒有密碼」這類敘述當成秘密。
SECRET_PATTERNS = [
    ("GitLab token", re.compile(r"glpat-[0-9A-Za-z_\-]{10,}")),
    ("API key", re.compile(r"\b(?:sk|ghp|gho|xox[abp])[-_][0-9A-Za-z_\-]{16,}")),
    ("Bearer token", re.compile(r"\bBearer\s+[0-9A-Za-z._\-]{16,}")),
    ("私鑰", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("連線字串", re.compile(r"(?i)\b(?:server|data source)\s*=\s*[^;\s]+\s*;")),
    ("帳密設定", re.compile(r"(?i)\b(?:password|passwd|pwd|user id)\s*[=:]\s*[\"']?[^\s\"'`|,;]{3,}")),
]


class Stop(Exception):
    def __init__(self, status, **fields):
        super().__init__(status)
        self.fields = {"status": status, **fields}


def read_doc(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return handle.read().replace("\r\n", "\n").strip() + "\n"


def read_description(feature_dir):
    """回傳 (檔名, 內文, 跳過原因)。"""
    found = [source for source in DESCRIPTION_SOURCES if os.path.isfile(os.path.join(feature_dir, source[0]))]
    if not found:
        return None, None, "沒有 " + " 或 ".join(name for name, _ in DESCRIPTION_SOURCES)
    if len(found) > 1:
        raise Stop("ambiguous_description", message="feature 目錄同時有 " + " 與 ".join(name for name, _ in found) + "，無法判斷要發布哪一份")
    name, status = found[0]
    candidate = read_doc(os.path.join(feature_dir, name))
    if re.search(rf"^文件狀態:\s*{status}\b", candidate, re.MULTILINE):
        return name, candidate, None
    return None, None, f"{name} 的文件狀態不是 {status}"


def normalize(text):
    """GitLab 會改寫表格分隔線與行尾，比對時要忽略。"""
    lines = (text or "").replace("\r\n", "\n").strip().split("\n")
    return "\n".join("|-|" if re.fullmatch(r"\|[\s:\-|]+\|", line.strip()) else line.rstrip() for line in lines)


def parse_url(url):
    match = URL_PATTERN.match(url.strip())
    if not match:
        raise Stop("bad_url", message="需要完整的 Issue URL，例如 https://host/group/project/-/work_items/60")
    return match.group(1), match.group(2), int(match.group(3))


def check_remote(host, project):
    try:
        remote = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return "match" if remote_path(remote).lower() == f"{host}/{project}".lower() else "mismatch"


def remote_path(remote):
    """把 https、ssh 與 scp 形式的 remote 都轉成 host/group/project。"""
    if "://" in remote:
        path = re.sub(r"^[a-z+]+://([^@/]+@)?", "", remote)
        path = re.sub(r"^([^/:]+):\d+/", r"\1/", path)
    else:
        path = re.sub(r"^[^@/]+@", "", remote).replace(":", "/", 1)
    return re.sub(r"\.git$", "", path.rstrip("/"))


def scan_secrets(documents):
    hits = []
    for name, text in documents:
        for number, line in enumerate(text.split("\n"), 1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    hits.append({"file": name, "line": number, "type": label})
    return hits


class GitLab:
    def __init__(self, glab, host, project, iid, work_dir):
        self.glab = glab
        self.env = {**os.environ, "GITLAB_HOST": host}
        self.base = f"projects/{urllib.parse.quote(project, safe='')}/issues/{iid}"
        self.work_dir = work_dir

    def _call(self, args):
        result = subprocess.run([self.glab, "api", *args], capture_output=True, env=self.env)
        if result.returncode != 0:
            raise Stop("gitlab_error", request=args[-1] if args else "", message=result.stderr.decode("utf-8", "replace")[:400])
        return json.loads(result.stdout.decode("utf-8"))

    def get_issue(self):
        return self._call([self.base])

    def get_notes(self):
        notes, page = [], 1
        while True:
            batch = self._call([f"{self.base}/notes?per_page=100&sort=asc&page={page}"])
            notes.extend(batch)
            if len(batch) < 100:
                return notes
            page += 1

    def _send(self, method, path, field, value, name):
        # 內容走檔案，避免中文、換行與引號經過 shell 跳脫。
        payload = os.path.join(self.work_dir, f"payload-{name}.json")
        with open(payload, "w", encoding="utf-8") as handle:
            json.dump({field: value}, handle, ensure_ascii=False)
        return self._call(["-X", method, path, "-H", "Content-Type: application/json", "--input", payload])

    def update_description(self, text):
        return self._send("PUT", self.base, "description", text, "description")

    def add_note(self, text, name):
        return self._send("POST", f"{self.base}/notes", "body", text, name)

    def update_note(self, note_id, text, name):
        return self._send("PUT", f"{self.base}/notes/{note_id}", "body", text, name)


def git_output(*args):
    result = subprocess.run(["git", *args], capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", "replace").strip()


def read_commits(base):
    merge_base = git_output("merge-base", base, "HEAD")
    if not merge_base:
        raise Stop("base_not_found", message=f"找不到目標分支 {base}，或它和 HEAD 沒有共同祖先")
    log = git_output("log", "--reverse", "--format=%h%x09%s", f"{merge_base}..HEAD") or ""
    commits = [line.split("\t", 1) for line in log.splitlines() if "\t" in line]
    if not commits:
        raise Stop("no_commits", message=f"HEAD 相對 {base} 沒有 commit")
    return commits


def split_ticket(doc, fallback_title):
    """拆出折疊標題與內文。票做完後 Status 只會誤導讀者，所以發布時拿掉；本地檔案不動。"""
    lines = doc.strip().split("\n")
    title = fallback_title
    if lines and lines[0].startswith("# "):
        title = lines.pop(0)[2:].strip()
    for index, line in enumerate(lines):
        if line.startswith("## "):
            break
        if re.match(r"^(\*\*)?Status:(\*\*)?\s", line):
            del lines[index]
            break
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return title, body


def escape_issue_refs(text):
    """票裡的 #3 多半是驗收項目編號，不跳脫的話 GitLab 會連到 Issue，還在對方留下系統紀錄。

    程式碼區塊與行內程式碼不會被 GitLab 當成參照，反斜線在那裡也會原樣顯示，所以略過。
    """
    lines, in_fence = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            segments = re.split(r"(`[^`]*`)", line)
            line = "".join(
                segment if index % 2 else re.sub(r"(?<![\\\w/&#])#(\d+)", r"\\#\1", segment)
                for index, segment in enumerate(segments)
            )
        lines.append(line)
    return "\n".join(lines)


def build_tickets_body(tickets, branch, base, commits):
    rows = "\n".join(f"| `{sha}` | {subject.replace('|', chr(92) + '|')} |" for sha, subject in commits)
    parts = [
        TICKETS_HEADING,
        f"分支 `{branch}` → `{base}`，共 {len(commits)} 個 commit。",
        f"| Commit | 內容 |\n| --- | --- |\n{rows}",
        # `---` 前要有空行，否則 GitLab 會把上一行當成標題。
        "---",
    ]
    for fallback, doc in tickets:
        title, body = split_ticket(doc, fallback)
        # summary 後與 details 前的空行不能省，否則裡面的 Markdown 不會被渲染。
        # 預設的 summary 是內文字級，票一多就不好掃視。標題在 HTML 內，跳脫要用字元參照。
        summary = re.sub(r"#(\d+)", r"&#35;\1", html.escape(title, quote=False))
        parts.append(f"<details>\n<summary><h3>{summary}</h3></summary>\n\n{escape_issue_refs(body)}\n\n</details>")
    return "\n\n".join(parts) + "\n"


def first_line(text):
    return (text or "").strip().split("\n", 1)[0].strip()


def find_note(notes, matches):
    for note in reversed(notes):
        if not note.get("system") and matches(first_line(note.get("body"))):
            return note
    return None


def describe_existing(old, new):
    old_text, new_text = normalize(old), normalize(new)
    if not old_text:
        return "empty", 1.0
    if old_text == new_text:
        return "same", 1.0
    ratio = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False).quick_ratio()
    return ("similar" if ratio >= 0.7 else "different"), round(ratio, 3)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="使用者提供的 Issue URL")
    parser.add_argument("--feature-dir", required=True)
    parser.add_argument("--base", help="這條分支的目標分支，用來算 commit 清單；要發布開發紀錄時必填")
    parser.add_argument("--skip", action="append", choices=["description", "tickets", "map"], default=[], help="這次不發布的部分，可重複指定")
    parser.add_argument("--apply", action="store_true", help="實際寫入 GitLab；沒帶時只預演")
    parser.add_argument("--on-existing", choices=["stop", "update"], default="stop", help="Issue 已有同類留言時的處理")
    parser.add_argument("--confirm-replace", action="store_true", help="使用者已確認可覆蓋差異很大的主內文")
    parser.add_argument("--confirm-secrets", action="store_true", help="使用者已確認秘密掃描的命中是誤判")
    parser.add_argument("--confirm-mismatch", action="store_true", help="使用者已確認目錄編號或 git remote 與 URL 不符仍要發布")
    parser.add_argument("--glab", default="glab", help=argparse.SUPPRESS)
    args = parser.parse_args()

    result = {"mode": "apply" if args.apply else "dry-run"}
    try:
        host, project, iid = parse_url(args.url)
        result.update(project=project, iid=iid)

        map_path = os.path.join(args.feature_dir, "acceptance-map.md")
        ticket_paths = sorted(glob.glob(os.path.join(glob.escape(args.feature_dir), "issues", "*.md")))
        # 流程可以抽掉步驟，所以每一部分都是有才發布，跳過的原因要回報給使用者。
        skipped = result["skipped"] = {name: "使用者指定跳過" for name in args.skip}
        doc = map_doc = tickets_body = None
        documents = []

        if "description" not in skipped:
            doc_name, doc, skip_reason = read_description(args.feature_dir)
            if doc:
                documents.append((doc_name, doc))
            else:
                skipped["description"] = skip_reason

        if "map" not in skipped:
            if os.path.isfile(map_path):
                map_doc = read_doc(map_path)
                documents.append(("acceptance-map.md", map_doc))
            else:
                skipped["map"] = "沒有 acceptance-map.md"

        if "tickets" not in skipped:
            if ticket_paths:
                if not args.base:
                    raise Stop("base_required", message="要發布開發紀錄時，需要 --base 指定目標分支")
                ticket_docs = [read_doc(path) for path in ticket_paths]
                documents.extend((os.path.basename(p), d) for p, d in zip(ticket_paths, ticket_docs))
                commits = read_commits(args.base)
                branch = git_output("branch", "--show-current") or "HEAD"
                tickets = [(os.path.splitext(os.path.basename(path))[0], ticket) for path, ticket in zip(ticket_paths, ticket_docs)]
                tickets_body = build_tickets_body(tickets, branch, args.base, commits)
                result["branch"] = branch
                result["commits"] = len(commits)
                unpushed = git_output("rev-list", "--count", "@{upstream}..HEAD")
                result["unpushed_commits"] = int(unpushed) if unpushed else None
                result["tickets"] = [os.path.basename(path) for path in ticket_paths]
            else:
                skipped["tickets"] = "沒有 issues/*.md"

        contents = {"description": doc, "tickets": tickets_body, "map": map_doc}
        if not any(contents.values()):
            raise Stop("nothing_to_publish", message="沒有可發布的內容")

        result["chars"] = {name: len(body) for name, body in contents.items() if body}
        if max(result["chars"].values()) > MAX_BODY_CHARS:
            raise Stop("too_large", message=f"單一內容超過 GitLab 上限 {MAX_BODY_CHARS} 字元", **{"chars": result["chars"]})

        blockers = []
        dir_numbers = re.findall(r"#(\d+)", os.path.basename(os.path.normpath(args.feature_dir)))
        result["dir_numbers"] = dir_numbers
        if dir_numbers and str(iid) not in dir_numbers and not args.confirm_mismatch:
            blockers.append("issue_number_mismatch")
        remote_state = check_remote(host, project)
        result["remote"] = remote_state
        if remote_state != "match" and not args.confirm_mismatch:
            blockers.append("remote_mismatch")

        secret_hits = scan_secrets(documents)
        result["secret_hits"] = secret_hits
        if secret_hits and not args.confirm_secrets:
            blockers.append("secret_hits")

        slug = re.sub(r"[^0-9A-Za-z_-]+", "-", project)
        work_dir = os.path.join(tempfile.gettempdir(), "to-gitlab-issue", f"{slug}-{iid}-{time.strftime('%Y%m%d-%H%M%S')}")
        os.makedirs(work_dir, exist_ok=True)
        result["backup_dir"] = work_dir

        gitlab = GitLab(args.glab, host, project, iid, work_dir)
        issue, notes = gitlab.get_issue(), gitlab.get_notes()
        # 備份必須先於任何寫入：GitLab 不一定保留主內文的歷史版本。
        with open(os.path.join(work_dir, "issue-before.json"), "w", encoding="utf-8") as handle:
            json.dump(issue, handle, ensure_ascii=False, indent=1)
        with open(os.path.join(work_dir, "notes-before.json"), "w", encoding="utf-8") as handle:
            json.dump(notes, handle, ensure_ascii=False, indent=1)
        for name, body in contents.items():
            if body:
                with open(os.path.join(work_dir, f"{name}.md"), "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(body)

        result["issue"] = {"title": issue.get("title"), "state": issue.get("state"), "url": issue.get("web_url")}
        if doc:
            kind, ratio = describe_existing(issue.get("description"), doc)
            result["existing_description"] = {"kind": kind, "similarity": ratio, "chars": len(issue.get("description") or ""), "author": (issue.get("author") or {}).get("username")}
            if kind == "different" and not args.confirm_replace:
                blockers.append("description_differs")

        ticket_note = find_note(notes, lambda line: line == TICKETS_HEADING) if tickets_body else None
        map_note = find_note(notes, lambda line: line.startswith(MAP_HEADING_PREFIX)) if map_doc else None
        result["existing_notes"] = {"tickets": ticket_note and ticket_note["id"], "map": map_note and map_note["id"]}
        if (ticket_note or map_note) and args.on_existing == "stop":
            blockers.append("notes_exist")

        result["blockers"] = blockers
        if not args.apply:
            result["status"] = "preview"
            return finish(result, 0)
        if blockers:
            result["status"] = "blocked"
            return finish(result, 1)

        done = result["written"] = []
        note_ids = {}
        if doc:
            gitlab.update_description(doc)
            done.append("description")
        for name, body, existing in (("tickets", tickets_body, ticket_note), ("map", map_doc, map_note)):
            if body:
                sent = gitlab.update_note(existing["id"], body, name) if existing else gitlab.add_note(body, name)
                note_ids[name] = sent["id"]
                done.append(f"{name}:{sent['id']}")

        after_issue, after_notes = gitlab.get_issue(), {n["id"]: n for n in gitlab.get_notes()}
        verify = {}
        if doc:
            verify["description"] = normalize(after_issue.get("description")) == normalize(doc)
        for name, note_id in note_ids.items():
            verify[name] = normalize((after_notes.get(note_id) or {}).get("body")) == normalize(contents[name])
        result["verify"] = verify
        result["status"] = "ok" if all(verify.values()) else "verify_failed"
        return finish(result, 0 if all(verify.values()) else 1)
    except Stop as stop:
        result.update(stop.fields)
        return finish(result, 1)


def finish(result, code):
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
