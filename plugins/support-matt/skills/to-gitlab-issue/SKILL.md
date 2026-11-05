---
name: to-gitlab-issue
description: 把本地文件發布到公司 GitLab 主 Issue，有什麼發什麼：issue-doc.md（final）替換主內文，issues/ 全部 ticket 留言一則開發紀錄，acceptance-map.md 留言一則，缺的部分跳過並回報。寫入前先備份 Issue 原內容到暫存目錄，寫入後讀回比對。使用者必須提供 Issue URL，沒給就問，不得從分支名、目錄名或 commit 推測編號。這是「GitLab 只讀」規則的明確例外，只在使用者調用本 skill 時成立。當使用者要把規格與盤點貼回 GitLab Issue、更新主 Issue 內文，或說「發布到 Issue」「貼上 Issue」「把文件送上 GitLab」時使用。
disable-model-invocation: true
---

# to-gitlab-issue

把 feature 目錄裡的文件送上主 Issue。本地文件是來源，GitLab 是發布目的地；這支不改任何本地文件。

工作流可以依案子抽掉步驟，所以三個部分都是**有才發布**：

| 部分 | 來源 | 什麼時候跳過 |
| --- | --- | --- |
| 主內文 | `issue-doc.md` | 沒有這個檔，或文件狀態不是 final。例如 Issue 已有開發文件，主內文就維持原樣 |
| 開發紀錄留言 | `issues/*.md` | 沒有 ticket |
| 驗收盤點留言 | `acceptance-map.md` | 沒有這個檔 |

使用者明確說這次不發某一部分時，帶 `--skip description`、`--skip tickets` 或 `--skip map`，可重複指定。跳過不是錯誤，但要在回報中講清楚，使用者才知道哪些沒有上去。

## 寫入權限（本 skill 的特例）

全域設定與 repo 的 `issue-tracker.md` 都寫 GitLab 只讀。**使用者調用本 skill 並提供 Issue URL，就是對那一張 Issue 的明確授權**，規則有矛盾時，在本 skill 內以這裡為準。

授權的範圍只有下面三件事，其餘一律維持只讀：

- 替換該 Issue 的主內文。
- 新增或更新「開發紀錄」與「驗收盤點」兩則留言。
- 讀取該 Issue 與留言。

不修改標題、標籤、指派、狀態，不關閉 Issue，不動其他人的留言，不開 MR，不 push。授權不延伸到其他 Issue，也不延伸到之後的對話。

## Issue URL 是必要輸入

使用者沒有提供 URL 時，**停下來要 URL**，不要猜。分支名、目錄名、commit message 裡的編號都不算：寫錯 Issue 會覆蓋別人的內文，而目錄上的 `#60` 只是線索，不是授權。

URL 只取使用者這次訊息給的那一個。

## 流程

`SKILL_DIR` 指這份 SKILL.md 所在目錄。

### 1. 定位 feature 目錄

依 `.ai/docs/agents/issue-tracker.md` 的慣例，通常是 `.ai/.scratch/<feature>/`。使用者有指定就用；沒有就依目前分支對應，對應不到或有多個候選時停下來問。

### 2. 預演

從 repo 根目錄執行，不帶 `--apply`：

```bash
python "SKILL_DIR/scripts/publish_issue.py" --url "<使用者給的 URL>" --feature-dir "<feature 目錄>" --base "<目標分支>"
```

`--base` 是這條分支要合併進去的分支，用來算 commit 清單，要發布開發紀錄時才需要。使用者沒說就問，不要猜：猜錯會列出不屬於這條分支的 commit。

預演結果的 `skipped` 列出這次不會發布的部分與原因，先轉告使用者。如果跳過的正好是使用者想發的，例如 `issue-doc.md` 還不是 final，就停下來讓使用者決定，不要自行改檔或硬發。

腳本不會寫入 GitLab，只會備份 Issue 現況到暫存目錄，組好內容，再印一行 JSON。`status` 是 `preview` 才繼續，其他值依下表處理。

| `status` | 意思 | 怎麼處理 |
| --- | --- | --- |
| `bad_url` | URL 格式不對 | 請使用者給完整 URL |
| `nothing_to_publish` | 三個部分都沒有可發布的內容 | 轉告 `skipped` 的原因並停止，不要自己補文件 |
| `base_required` | 要發布開發紀錄，但沒有 `--base` | 請使用者提供目標分支 |
| `base_not_found` | 找不到 `--base`，或它和 HEAD 沒有共同祖先 | 請使用者確認目標分支 |
| `no_commits` | HEAD 相對 `--base` 沒有 commit | 告知使用者並停止，可能在錯的分支 |
| `too_large` | 內容超過 GitLab 上限 | 告知使用者，不要自行截斷 |
| `gitlab_error` | `glab` 讀取失敗 | 轉告 `message`。未登入時請使用者自己跑 `! glab auth login` |

### 3. 處理 blockers

預演結果的 `blockers` 是要使用者決定的事。逐項轉告，等使用者回答，再帶對應參數。**這些是使用者的決定，不要自行加參數通過。**

| blocker | 情況 | 通過方式 |
| --- | --- | --- |
| `issue_number_mismatch` | 目錄名的編號和 URL 不同，可能貼錯 Issue | 使用者確認後 `--confirm-mismatch` |
| `remote_mismatch` | 目前 repo 的 `origin` 和 URL 的專案不同，或查不到 | 使用者確認後 `--confirm-mismatch` |
| `description_differs` | 現有主內文和 `issue-doc.md` 差異很大，可能是別人寫的需求 | 給使用者看 `issue-before.json` 的內文摘要與作者，確認後 `--confirm-replace` |
| `notes_exist` | Issue 已有同類留言，可能是重跑 | 使用者同意更新後 `--on-existing update`，會就地改那兩則，不會多留一份 |
| `secret_hits` | 秘密掃描命中，結果只列檔案與行號 | 自己去看該行，**不要把值貼進對話**。真的是秘密就停下來請使用者清除；確認誤判後 `--confirm-secrets` |

掃描只是最後一道防線，抓不到所有形式。檔案裡有 commit hash、`.ai/` 路徑這類內部資訊屬正常，不算秘密，內容照原文帶入。

沒有 blockers 時，使用者調用本 skill 就已授權，不必再問一次，直接進下一步。

### 4. 寫入

同一行指令加上 `--apply` 與前一步確定的參數：

```bash
python "SKILL_DIR/scripts/publish_issue.py" --url "<URL>" --feature-dir "<feature 目錄>" --base "<目標分支>" --apply
```

腳本依序更新主內文、開發紀錄、驗收盤點中要發布的部分，再讀回比對。讀回時會忽略表格分隔線與行尾空白，因為 GitLab 會改寫它們。

- `status: ok`：完成。
- `status: blocked`：有 blockers 尚未處理，什麼都沒有寫入。回到第 3 步。
- `status: verify_failed`：內容已送出但讀回不一致。看 `verify` 是哪一項，連同備份路徑轉告使用者。
- `status: gitlab_error`：寫到一半失敗。`written` 列出已完成的部分。不要手動補做，查明原因後用 `--on-existing update` 重跑，已寫入的留言會就地更新，不會重複。

### 5. 回報

告知使用者：

- Issue 連結與標題。
- 每一部分的結果：已發布的附留言 note id，跳過的附原因。
- 備份目錄的完整路徑。原內文在 `issue-before.json`，暫存目錄不會永久保留，要留存請使用者自行搬走。
- 預演時使用者確認過的事項，例如覆蓋了差異很大的內文。

`push` 與開 MR 不在範圍內。`unpushed_commits` 大於 0 時提醒使用者：這些 commit 列在清單裡，但 push 前 GitLab 連不到它們。只提醒，不動手。

## 留言格式

開發紀錄開頭是分支與 commit 清單，補上票裡看不到的內容，例如 review 後才加、不屬於任何一張票的修正。commit 從 `git log` 取得，不對應到每張票，因為不是每張票都記有交付 commit。

每張票依檔名排序，各自收進預設折疊的 `<details>`：同一則留言裡票一多就很難捲動。票的第一行 `# 01: 標題` 會變成折疊標題，包在 `<h3>` 裡，因為預設的 `<summary>` 只有內文字級，不好掃視。內文其餘原樣帶入，只有兩處調整，本地檔案都不動：

- 拿掉 `Status:` 那一行，因為做完後它只會誤導讀者。
- 把 `#3` 跳脫成 `\#3`。票裡的這類編號多半指驗收項目，不跳脫的話 GitLab 會連到同編號的 Issue，還在對方留下一筆系統紀錄，事後刪不掉。行內程式碼與程式碼區塊不會被當成參照，所以不動。

```md
# 開發紀錄（TICKETS）

分支 `<分支>` → `<目標分支>`，共 N 個 commit。

| Commit | 內容 |
| --- | --- |
| `<hash>` | <commit 標題> |

---

<details>
<summary><h3>01: <票的標題></h3></summary>

...

</details>

<details>
<summary><h3>02: <票的標題></h3></summary>

...

</details>
```

驗收盤點就是 `acceptance-map.md` 的全文。主內文就是 `issue-doc.md` 的全文。三者都會去掉 BOM 並把 CRLF 轉成 LF，本地檔案不受影響。

腳本用留言的第一行認出既有留言：`# 開發紀錄（TICKETS）` 與開頭為 `# 驗收盤點` 的留言。不要手動改這兩行，否則重跑時會認不出來而多留一份。

## 適用範圍

只處理走 `to-issue-doc` 的 feature。重案流程的 `engineering-spec.md` 要先轉成交付版，檔名與貼法不同，目前不支援，遇到時告知使用者並停止。

## 工作流位置

```text
[to-issue-doc final] → [to-acceptance-map] → [to-gitlab-issue] → 使用者自行 push、開 MR
```

這是完整流程的順序，前兩步都可以抽掉。之後文件有修訂，重新調用本 skill 並確認更新既有留言即可。
