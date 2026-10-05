---
name: to-change-request
description: 開發中途發現需要改動時的再入點：接在 grill 之後、implement 之前，一次做完需求與設計文件的同步並修訂受影響的未完成 ticket，取代手動依序調用 to-spec、to-engineering-spec。先分流本次改動屬於純實作、設計層級或需求層級，純實作直接請使用者去 implement 不動任何文件；需要動文件時對 spec.md 只做 delta 編輯（不重寫整份、不重新 publish），設計與驗證條件一律委派該 feature 的規格文件 skill（to-issue-doc 或 to-engineering-spec）修訂模式，每份產物不論改或不改都列出結果與理由，一起攤出來讓使用者確認，通過後就地修訂未完成的 ticket 並停止。需要新票時不自己開，改給出插入位置與字尾票號（例如 04a），輸出一行交給 to-tickets；已完成的票一律不動。本 skill 不寫程式、不跑 code-review、不做定稿、不建立或修改任何遠端 Issue。當使用者在 branch 開發到一半發現需求或設計要調整、剛 grill 完要把結論同步回文件與 ticket 時使用。
---

# to-change-request

開發中途改變主意時的**再入點**。接在 grill 之後、`implement` 之前，把 grill 的結論同步進 `spec.md` 與本 feature 的規格文件，並修訂受影響的未完成 ticket；需要新票時，給出票號交給 `to-tickets`。

> **規格文件指哪一份**：預設是 `issue-doc.md`，修訂委派給 `to-issue-doc`（修訂模式）；重案流程（動角色權限、schema、跨模組交易）是 `engineering-spec.md`，委派給 `to-engineering-spec`（修訂模式）。以哪一份實際存在於 feature 目錄為準，兩份都在時以 `engineering-spec.md` 為準。**本檔以下一律寫 `engineering-spec.md`，那些敘述對 `issue-doc.md` 同樣成立**——差別只有委派對象與狀態名稱（`定稿` 對應 `final`）。

## 工作流位置

```text
（開發中途發現要改）
  → grill-me / grill-with-docs（使用者自己跑，取得共識）
  → [to-change-request]  ← 本 skill：分流 → 同步 spec → 同步 engineering-spec → 一個確認關卡 → 修訂未完成 ticket
  → （需要新票時）to-tickets，依本 skill 給的票號插入
  → implement-stepwise
```

它**不是**主線流程的一站。第一次做這個功能時走的是 `to-spec → to-engineering-spec → to-tickets`；本 skill 只服務「已經有 spec、開發到一半、要改」這個情境。

## 為什麼需要這一層

**Matt 原生流程在這裡是斷的。** `to-spec` 只有「把對話 synthesize 成一份 spec 並 publish」一種行為，沒有修訂模式——中途重跑會重寫整份規格。所以 Matt 的中途改動走的是 `grill → implement`，`spec.md` 根本不會同步。原生設計如此並無不妥（Matt 的 spec 是拋棄式的工作稿），但本 plugin 的 `engineering-spec.md` 是**會被就地修訂、且是下游驗收基準的權威**，它必須跟上。

手動補這個斷點要依序跑多支 skill、通過多個確認關卡。本 skill 把文件同步與修票收成一次調用、一個關卡；新票仍由 `to-tickets` 拆。

**它不重寫任何一支上游 skill。** 分工如下：

| 這一段 | 怎麼做 | 為什麼 |
| --- | --- | --- |
| grill | **不在本 skill 內** | `grill-me` 與 `grill-with-docs` 都是 `disable-model-invocation: true`，model 觸發不到；而且該選哪一支、要 grill 到什麼程度，是使用者的決定 |
| `engineering-spec.md` 的修訂 | **真委派**：調用 `to-engineering-spec`（修訂模式） | 它是本 plugin 自己的 skill，可被 model 調用。委派才不會讓修訂規則分岔成兩份 |
| `spec.md` 的 delta 編輯 | 本 skill 就地做 | `to-spec` 呼叫不到，而且它做的是「重寫整份」，不是本 skill 要的 delta |
| 修訂未完成的 ticket | 本 skill 就地做 | 改的是既有切片的內容，不涉及重新切片；交給 `to-tickets` 反而會重切一整組票 |
| 新票 | **交給 `to-tickets`**，本 skill 只給範圍、插入位置與票號 | 切片是 `to-tickets` 的本體，本 skill 自己開票只會養出一套與它分岔的切片規則。它預設從 `01` 編號，所以交接那一行要把範圍與票號寫死 |

## 入口

**本 skill 從「共識已經達成」開始。** 它不訪談、不 grill、不重新論證方向——那些在調用之前就該做完。

合法的入口有三種，處理方式相同：

1. 剛跑完 `grill-me` 或 `grill-with-docs`，結論在當前對話裡。**兩者對本 skill 沒有差別**——差別在 grill 過程要不要查文件，產出到本 skill 手上時都是「對話裡的共識」。`grill-with-docs` 若順帶產生了 ADR，一併讀進來。
2. 使用者直接口述一項已經想清楚的改動。
3. `code-review` 或測試過程中發現的問題，使用者已決定怎麼改。

**共識不足時停下來。** 使用者只丟一句「這裡好像怪怪的」而沒有結論，不要自行決定改法後往下跑——回一句請他先 grill。本 skill 的每一步都假設「要改成什麼」已經定案。

## 分流（第一步，也是最省事的一步）

讀完現況後，先判定本次改動的層級。**這一步決定後面跑不跑得下去，不要略過。**

| 層級 | 判準 | 處置 |
| --- | --- | --- |
| **純實作** | 不改任何人看得到的行為、不改設計決策、不改驗證條件。換寫法、抽方法、改變數命名、補防呆、修一個沒寫進規格的 bug | **停手**。明說「不需要動文件」並說出判為純實作的依據，請使用者直接去 `implement`。**不要為了留紀錄而動文件** |
| **設計層級** | 需求沒變，但落點、契約、資料結構、交易邊界、驗證條件要調整 | 不碰 `spec.md`；委派 `to-engineering-spec` 修訂 |
| **需求層級** | 要不要做、做到什麼程度變了：新增或刪除 user story、範圍進出、行為改變 | `spec.md` 做 delta 編輯，**接著一律委派** `engineering-spec.md` 修訂，由它判斷要不要改 |

判不出來時**問使用者，一句話就好**。猜錯的代價不對稱：把需求層級誤判成純實作，`spec.md` 與 `engineering-spec.md` 會從此與實作分岔，而且**沒有任何徵兆**——下游 `to-acceptance-map` 要等到 branch 收尾才會發現驗收基準是錯的。

三類都可能同時出現。以最高層級為準跑完整流程，純實作的部分不進文件。

## 執行流程

### 1. 定位與讀取

依 `.ai/docs/agents/issue-tracker.md` 的慣例定位 feature 目錄（通常 `.ai/.scratch/<feature-slug>/`）。使用者未指定時依當前 git 分支名稱推斷；推斷不出來就停下來問，不要猜。

讀進來：

- `spec.md` —— 需求權威，**必要**。
- `engineering-spec.md` —— 設計與驗證條件的權威（可能不存在，見下方防呆）。
- `issues/` 底下全部 ticket —— 取得編號、相依關係、哪些已完成（判準見「ticket 修訂規範」）。
- `.ai/docs/adr/` 中相關的 ADR、`.ai/CONTEXT.md`（術語一律對齊它）。

**三種要先停下來的狀態：**

| 觀察到 | 處置 |
| --- | --- |
| `spec.md` 不存在 | 這條 branch 沒走過 Matt 流程。停手，請使用者跑 `/to-spec`，本 skill 沒有東西可以 delta |
| `engineering-spec.md` 不存在 | 這個功能當初判定不需要正式規格。**不要順手幫他補一份**——那是 `to-engineering-spec` 建立模式的事，而且要先過適用門檻。告知使用者，取得同意後才只做 spec delta 與 ticket 修訂 |
| `engineering-spec.md` 的 `文件狀態` 是 `定稿` | 開發已經收尾過一輪。停下來確認：這是同一條 branch 的續作（確認後把狀態退回 `可拆 Ticket` 再修訂），還是該開新的 feature？**不要在定稿文件上靜默續改** |

### 2. 分流

依上一節判定。純實作 → 回報後停手，流程結束。

### 3. 同步 `spec.md`（僅需求層級改動）

**只做 delta 編輯。** 規範見下方「`spec.md` 的編輯授權」。

### 4. 委派 `to-engineering-spec` 修訂模式

設計層級與需求層級**一律委派**，本 skill 不先判斷規格文件要不要改——哪些內容屬於該文件、哪些不屬於，只有它自己的規則說得清楚（例如 `issue-doc.md` 的 brief 只寫約束，資料模型、介面這類紀錄留到 final 才補）。

調用該 skill，並明確告知：這是**修訂模式**、改動內容是什麼、`spec.md` 已經（或不需要）同步。它自己會處理權威歸屬、`VC-xx` 的就地改寫、修訂紀錄與送出前自檢——**本 skill 不重述那些規則，也不繞過它直接改 `engineering-spec.md`**。

它判斷不需修改時，**取得它的理由並原樣轉述**，不要只轉述「不需修改」。

它停下來要求裁決時（衝突處理、需求層級事實誤入設計文件），**照它的要求把問題轉給使用者，不要代答**。

### 5. 確認關卡（本 skill 唯一的關卡）

**每份產物固定列一行，改或不改都要寫**；「未改」一定附理由（分流判準，或規格文件 skill 給的理由）：

```text
spec.md            已改：User Story 7 改寫（原文 → 新文見下）
engineering-spec   未改：本次只動畫面欄位順序，不涉及已確認的設計決策與 VC-xx
issues/ 修訂       05：驗收條件第 3 條改寫；06：Blocked by 加上 04a
issues/ 新票       需要 1 張，插在 04 與 05 之間，票號 04a，涵蓋 User Story 9
```

逐行下面再攤細節：

- `spec.md` 改了哪幾段，改成什麼（原文 → 新文）。
- 規格文件改了哪些章節、哪幾條 `VC-xx` 被改寫或刪除。
- **ticket 修訂**：每張要改的未完成票，原文 → 新文。
- **被推翻的已完成票**：哪些已完成的票所交付的行為被這次改動推翻——它們不改，靠新票收掉，在這裡點名讓使用者知道。
- **新票**：插入位置、票號、預計涵蓋的範圍；不寫完整草案，切片是 `to-tickets` 的事。

**未取得使用者確認前不改任何 ticket 檔案。** 收到修正意見時回到第 3、4 步改完再攤一次。

### 6. 修訂 ticket

確認通過後才改。規範見下方「ticket 修訂規範」。

### 7. 停止並回報

回報：分流結果、第 5 步那份逐產物清單（照最終狀態更新）、修訂了哪些票。最後給一行可直接貼上的下一步：

- **有新票** → 交給 `to-tickets`，範圍與票號寫死，見下方「新票交給 `to-tickets`」。
- **沒有新票** → 
  ```text
  $implement-stepwise 依 .ai/.scratch/<feature-slug>/issues/<NN>-<slug>.md
  ```

**本 skill 不自行調用 `to-tickets` 或任何 implement skill。**

## `spec.md` 的編輯授權

`to-engineering-spec` 規定「頂部一行指標是唯一允許對 Matt Spec 做的改動」——**那條規範的對象是 `to-engineering-spec` 自己**，理由是設計文件不該回頭改需求文件的內容。本 skill 的角色不同：它是需求變更的處理者，`spec.md` 的 delta 編輯正是它的職責之一。

授權範圍到此為止，以下是硬規則：

- **只改受本次變更影響的段落。** 沒被影響的一個字都不動，不順手潤稿、不重排章節、不補齊當初就沒寫的東西。
- **不重寫整份、不重新 publish、不改檔名、不另存副本。** 就地改同一份。
- **維持 Matt 的 spec 模板結構**（Problem Statement / Solution / User Stories / Implementation Decisions / Testing Decisions / Out of Scope / Further Notes）。不新增章節、不加欄位。
- **user story 的編號**：新增的接在最後，不插號、不重排；被取消的**改寫或刪除那一條**，不留一條矛盾的舊條文並存。刪除時在 `Out of Scope` 補一句說明它為什麼被拿掉。
- **不在 `spec.md` 加變更紀錄章節。** 變更理由記在 `engineering-spec.md` 的「修訂紀錄」一列，並在該列註明同時改了 `spec.md` 的哪一段——那份文件本來就有這個欄位，兩邊各記一份只會分岔。`engineering-spec.md` 不存在時，靠 git history，不要為此在 `spec.md` 長出一個 Matt 模板沒有的章節。
- **設計事實不要留在 `spec.md`。** 這次 grill 產生的落點、契約、責任歸屬，寫進 `engineering-spec.md`；`spec.md` 的 `Implementation Decisions` 只留需求層級的敘述。兩邊各留一份完整敘述，就是下一次的衝突來源（見 `to-engineering-spec` 的「單邊遺漏」）。

## ticket 修訂規範

**已完成的票一律不動**——不改內容、不改 checkbox、不刪除。它是交付紀錄，這條規則與 `to-engineering-spec` 定稿模式、`to-acceptance-map` 一致。被推翻的行為靠新票收掉，靠 `engineering-spec.md` 的 `VC-xx` 記錄現行事實。

**判定已完成**：ticket 末尾已有 `implement-stepwise` 收尾寫回的「驗收核對」章。沒有該章、但 git log 已有指向這張票的 commit 時，代表正在實作中，**停下來問使用者**，不要自行修訂。

未完成的票可以就地修訂，規則：

- **只改受本次變更影響的部分**：`What to build`、驗收條件、`Blocked by`。沒被影響的一個字都不動。
- **不改票號、不改檔名、不刪票、不合併票。** 未完成的票整張被取消時，不在本 skill 處理，見下方「退場」。
- 維持 Matt `to-tickets` 的 `<local-ticket-template>` 原格式，不新增欄位。
- ticket 內**不寫檔案路徑與程式碼片段**（Matt 的規則，會很快過期）。
- 不加「本票經 change request 修訂」之類的來源註記。追溯靠 `engineering-spec.md` 的修訂紀錄，不靠在 ticket 上長欄位。
- **不 publish 到任何遠端 tracker。**

## 新票交給 `to-tickets`

本 skill **不自己開新票**。需要新票時，由本 skill 決定插入位置與票號，輸出一行交給使用者貼給 `to-tickets`。

**插入位置**：使用者依票號順序開發，新票要插在它實際該被做的位置——排在它依賴的票之後、第一張應該等它完成的未完成票之前。**不得早於最後一張已完成的票**，那個位置已經過去了。

**票號用字尾插號，不重編既有票**：

- 插在 `04` 與 `05` 之間 → `04a`；同一位置要兩張 → `04a`、`04b`；`04a` 已存在 → 接著用下一個字母。
- 排在最後 → 接在最大號之後的下一個整數。
- 重編會讓檔名、`Blocked by`、已寫進 commit message 的票號全部對不上，所以一律不重編。`04-…` < `04a-…` < `05-…` 的檔名排序剛好是開發順序。

**後續票的 `Blocked by`**：應該等新票完成的未完成票，在第 6 步就把新票號加進它的 `Blocked by`，不留給 `to-tickets`。

交接那一行把範圍、票號與既有票的關係寫死：

```text
$to-tickets 只拆 .ai/.scratch/<feature-slug>/spec.md 的 User Story 9（本次新增），不要動 issues/ 既有的票；新票依序編號 04a（插在 04 與 05 之間），Blocked by 04
```

## 退場

命中下列任一條，就是切片本身要重做，**停手**交給 `to-tickets` 重拆剩餘部分：

- 未完成的票整張被取消，或需要刪除、合併既有票。
- 這次改動讓未完成票之間的相依順序整組要重排，不是插一兩張票就能解決。

這不是保守，是分界：「修一張票、插一張票」和「重排一組票」是兩件事。後者需要重算整張相依圖，那本來就是 `to-tickets` 的本體。

退場時，前面的文件同步**照樣做完**（那是本 skill 的價值所在），只在 ticket 這一步停下來，輸出一行給使用者貼：

```text
$to-tickets 依 .ai/.scratch/<feature-slug>/spec.md 與 engineering-spec.md 重拆未完成的部分，已完成的票不動
```

## 執行限制

本 skill **不負責**下列事項，出現時停下來導引使用者用對應的 skill：

- 寫程式、跑測試（`implement-stepwise`）。
- review 程式碼（`code-review`）。
- `engineering-spec.md` 的**定稿**（`to-engineering-spec` 定稿模式，發生在整條 branch 收尾時，不是每次改動）。
- 產出交付版（`engineering-spec-deliverable`）、盤點測試覆蓋（`to-acceptance-map`）。
- 建立、更新、留言或關閉任何遠端 Issue。GitLab 維持唯讀。

寫完檔案後停止，**不自行調用下一支 skill**。
