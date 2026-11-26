---
name: implement-parallel
description: 經 Herdr 並行實作同一份 spec 的多張票：主 session 依依賴圖調度，每張票由票級 agent 在獨立 worktree 實作，使用者逐票確認後才 squash 成整合分支上的一個票級 commit，全票合入後固定跑一次 Matt 雙審。
disable-model-invocation: true
---

# implement-parallel

依 `to-tickets` 的依賴圖，在**一條整合分支**上並行實作同一份 spec 的多張票。主 session 負責調度，每張票交給一個經 Herdr 開出的**票級 agent**，在各自的 worktree 實作。

本 skill 的形狀：

- **執行單位**：一份 spec 的全部票。
- **前提**：在 Herdr 環境中執行。沒有 Herdr 時停下來，建議改用逐張的 `implement-stepwise` 或 Matt 原生的 `implement-spec`。
- **人工關卡**：開場計畫、共用設計的提早確認（只在有票等它時）、每張票的**送審**。
- **commit**：票級 agent 在自己的票分支上自由 commit。整合分支只會出現使用者確認過的票級 commit，一張票一個，由 script 以 `merge --squash` 產生，歷史是線性的。
- **雙審**：票級雙審選用，命中條件時建議、使用者要求才執行。全票合入後，對整合分支**固定**跑一次。

## 角色

- **主 session**：調度、合入與寫回 ticket，也是使用者唯一的對話窗口。它不寫功能程式碼，所以也是使用者的顧問，見「主 session 當顧問」。
- **票級 agent**：一張票一個，契約見 [`references/ticket-agent.md`](references/ticket-agent.md)。
- **雙審 agent**：執行 `mattpocock-skills:code-review` 的 agent，由參數 `review` 決定是 Claude 或 Codex。

**Herdr 的操作方式依 Herdr 協作規則與相關 skill**，本 skill 只寫要交代對方的內容：誰開誰、在哪個目錄、執行什麼、結果回報給誰。

## 核心規則（最高優先）

- **整合分支只透過 `ticket_git.py merge --apply` 前進**，而且只在使用者確認該票的送審內容之後。確認只涵蓋使用者指名的票與該次送審的內容；共用設計的提早確認只涵蓋該設計。
- **轉給票級 agent 的只有工作指示**（修改、審查、解衝突），不轉達任何確認。提交與合入都由主 session 執行，票級 agent 不需要使用者的確認。
- **調度狀態以 `state.md` 為準。** 狀態一變就寫入，對話記憶不算數，見「狀態檔與恢復」。
- **主 session 不 push、不開 MR、不動遠端。**

## 前置讀取

1. `.ai/docs/agents/issue-tracker.md`（找不到改讀 `docs/agents/issue-tracker.md`），取得 feature 目錄與 ticket 位置。兩者皆無時停下來，請使用者先執行 `setup-matt-preset`。
2. feature 目錄下的全部 ticket，從 **Blocked by** 建立依賴圖。

ticket 與 `.ai/` 常列在 `.git/info/exclude`，**只存在於主 checkout**，worktree 裡看不到。交給任何 agent 的路徑一律用主 checkout 的絕對路徑。

本 skill 的工作目錄是 feature 目錄下的 `parallel/`（以下稱 **parallel 目錄**），放 `state.md` 與各票的送審檔案。

## 1. 開場

1. **確認參數。** 調用時要指定兩個值：`impl` 是票級 agent 用 `claude` 或 `codex`，`review` 是雙審 agent 用 `claude` 或 `codex`。缺哪個就用選項視窗問哪個，兩個都缺就在同一個視窗一起問。**不設預設值、不標建議**；環境沒有選項視窗時改用文字列出選項。
2. **決定整合分支。** 基底是 repo 的目標分支（一般是 `main`），分支名稱依 repo 慣例。主 checkout 要切到整合分支，切之前確認沒有未提交的已追蹤變更。
3. **列出計畫並停下等使用者確認**：整合分支與基底、`impl` 與 `review`、依賴圖、第一批可開工的票（**frontier**）、同時進行的上限（預設 3 張）。使用者確認計畫，即授權票級 agent 在各自的票分支上 commit。
4. 確認後建立整合分支，寫出 `state.md`，進入派工。

## 2. 派工

frontier 上的每張票（同時進行的不超過上限）：

1. 從整合分支目前的 tip 建立票分支與 worktree：`git worktree add -b ticket/<NN> <worktree 路徑> <整合分支>`。worktree 放在 repo 之外的同層目錄，例如 `<repo 名稱>-wt/<NN>-<slug>`。
2. 經 Herdr 開一個 `impl` 指定的 agent，工作目錄是該 worktree，交代：
   - 依 `references/ticket-agent.md` 的契約實作這張票（給該檔的絕對路徑）；
   - ticket、主 checkout、parallel 目錄的絕對路徑，以及整合分支名稱與 `review` 的值；
   - 送審、提早確認或卡住時，經 Herdr 回報給主 session。
3. 寫入 `state.md`。

**依賴以「已合入整合分支」為準。** 前置票送審了、使用者確認了它的設計，都還不算；要等它的票級 commit 進了整合分支，後續的票才從包含它的版本開工。

## 3. 進行中

- **共用設計的提早確認。** 票級 agent 遇到會影響其他票、又沒有既有範例可循的設計決策（例如共用服務的公開介面、同一狀態的命名、交易責任落在哪一層）時，會先回報那一段可運作的程式碼與待決問題。主 session 把它和受影響的票一起交給使用者決定，再把決定轉給相關的票級 agent。其餘的票照常進行。
- **實作中才發現兩張票會碰同一塊。** 讓後來的那張暫停受影響的部分，其餘能獨立做的繼續。
- 票級 agent 回報卡住（ticket 與程式碼不符、驗收條件矛盾、規模明顯超出）時，轉給使用者決定。ticket 本身有誤時，建議回 `to-tickets` 或 `to-change-request` 修正。

## 4. 送審

票級 agent 回報可送審後，主 session 讀它的 `report.md`，把摘要交給使用者：

- 檔案路徑：`report.md`、`diff.patch`（含新增檔案的完整 diff）、`message.txt`；
- 最值得看的地方：分層、責任、命名、註解或測試；
- 驗收判定、實際跑過的測試範圍與結果、Test Consolidation 與跨層重複檢查的結論；
- 完整的 commit message；
- 命中下列任一條時，附上票級雙審的建議與依據，沒命中就不提：
  1. 本票新增了共用介面，而且還有未開工的票要接在上面做；
  2. diff 實際動到 schema、資料遷移或不可逆操作（刪除、覆寫外部狀態）。

多張票可以一起送審，但已就緒的票不必等其他票。使用者可以在一次回覆中分別處理多張票：

- **確認** → 進第 5 節。
- **要修改** → 把修改要求轉給原票級 agent，它修正、重驗後會重新送審。
- **審查** → 進第 6 節。
- 回覆不明確 → 當作尚未確認，問清楚。

## 5. 合入與寫回

逐張處理，一次只合入一張：

1. 確認票級 agent 已停下、worktree 沒有未提交的變更。
2. **預演**：`python "SKILL_DIR/scripts/ticket_git.py" merge --repo <主 checkout> --integration <整合分支> --ticket-branch ticket/<NN> --worktree <worktree> --message-file <parallel 目錄>/<NN>/message.txt`
   - `conflict` → 請票級 agent 把最新的整合分支併進票分支、解衝突、重跑受影響的測試，並更新送審檔案。解衝突改到使用者看過的內容時，把受影響的 diff 重新送審。
   - 其他非 `preview` 的狀態 → 照實回報，不繞過檢查。
3. **提交**：同一行指令加上 `--apply`，把回傳的 commit 寫進 `state.md`。
4. **寫回 ticket**：`python "SKILL_DIR/scripts/ticket_git.py" writeback --repo <主 checkout> --ticket <ticket> --record <parallel 目錄>/<NN>/record.md --commit <票級 commit>`
5. **清理**：關掉該票的 Herdr 終端機，`git worktree remove <worktree>`（不加 `--force`；被拒絕就回報），再用 `git branch -D ticket/<NN>` 刪掉票分支。squash 合入後 git 不會把票分支視為已合併，所以要用 `-D`；內容已由 script 比對 tree 確認進了整合分支。
6. 重新計算 frontier，派出新解鎖的票。

## 6. 票級雙審（使用者要求才執行）

把「審查」轉給該票的票級 agent，它依契約執行雙審，結果寫進 `review.md`。主 session 把報告照兩軸格式原樣交給使用者，**每一項附上主 session 自己的建議（採納或不採納）與理由，並標明這是主 session 的看法**，由使用者決定。

採納的項目轉給原票級 agent 修正，修正後重新送審。審查不會自動重跑，要不要再審由使用者決定。使用者的採納與不採納（含理由）由主 session 補進該票 `record.md` 的審查紀錄，格式依 `wrap-up-rules.md` 的「寫回 ticket」。

## 7. 整合分支收尾

全部的票合入後：

1. **整體驗證**：跑整合分支 diff 涉及的測試專案，有 `.ai/docs/agents/testing.md` 時改用它定義的執行單位，逐一執行。
2. **固定雙審**：fixed point 是整合分支的起點，規格來源是 feature 目錄的 `spec.md`。`review` 與主 session 是同一家時，直接調用 `mattpocock-skills:code-review`；不同家時，經 Herdr 開 `review` 指定的 agent，在主 checkout 執行。報告的呈現方式同第 6 節。
3. **修正**：採納的項目交給一個新的票級 agent，用同樣的方式開一個修正用的 worktree，走送審與合入。這次沒有 ticket 可寫回，結果記在 `state.md`。
4. **檢查殘留**：`git worktree list` 與 `state.md` 中還有未清理的 worktree 時，列給使用者。
5. 回報整合分支的 commit 清單，提示接著跑 `to-feature-doc final`，再開新 session 跑 `to-acceptance-map`。**回報完就停。**

## 狀態檔與恢復

`state.md` 開頭記整合分支、基底 commit、`impl` 與 `review`，接著一張表：

```md
| 票 | 狀態 | 票分支 | worktree | Herdr 終端機 | 票級 commit |
| --- | --- | --- | --- | --- | --- |
| 01 | 已合入 | ticket/01 | （已清理） | （已關閉） | a1b2c3d |
| 02 | 送審中 | ticket/02 | ../repo-wt/02-xxx | t-02 | |
| 03 | 待開工（等 01） | | | | |
```

狀態依序為：待開工、實作中、等待設計確認、送審中、修改中、已合入。

**compact 或換新 session 之後，先重建現況再繼續**：讀 `state.md`、`git worktree list`、整合分支的 log，以及各票 parallel 目錄裡的送審檔案。三者不一致時以 git 為準，並告知使用者哪裡不一致。原本的票級 agent 已不存在時，開一個新的接手同一個 worktree，草稿與送審檔案都還在磁碟上。parallel 目錄留有 `test.lock`、但沒有任何票級 agent 正在跑測試時，那是中斷留下的鎖，告知使用者後移除。

## 主 session 當顧問

使用者會在開場、送審、雙審之後請主 session 解釋或給建議。主 session 沒有寫這些程式碼，可以直接給建議與理由。

- 只看一兩段程式就答得出來的，直接讀相關的 hunk，不把整份 diff 讀進來。
- 要追呼叫鏈、比較多處既有寫法時，交給 sub-agent 去讀，只收結論。主 session 的 context 要留給調度。
