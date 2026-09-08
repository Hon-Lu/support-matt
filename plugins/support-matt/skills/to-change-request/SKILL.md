---
name: to-change-request
description: 開發中途發現需要改動時的再入點：接在 grill 之後、implement 之前，一次做完需求與設計文件的同步並追加 ticket，取代手動依序調用 to-spec、to-engineering-spec、to-tickets。先分流本次改動屬於純實作、設計層級或需求層級，純實作直接請使用者去 implement 不動任何文件；需要動文件時對 spec.md 只做 delta 編輯（不重寫整份、不重新 publish），設計與驗證條件委派 to-engineering-spec 修訂模式，兩份改動一起攤出來讓使用者確認，通過後在 issues/ 追加 ticket 並停止。追加上限為兩張票且不得重排既有票的相依順序，超過就停手請使用者改跑 to-tickets 重拆。本 skill 不寫程式、不跑 code-review、不做定稿、不建立或修改任何遠端 Issue。當使用者在 branch 開發到一半發現需求或設計要調整、剛 grill 完要把結論同步回文件並接著開票時使用。
---

# to-change-request

開發中途改變主意時的**再入點**。接在 grill 之後、`implement` 之前，把 grill 的結論同步進 `spec.md` 與本 feature 的規格文件，並追加一張 ticket。

> **規格文件指哪一份**：預設是 `issue-doc.md`，修訂委派給 `to-issue-doc`（修訂模式）；重案流程（動角色權限、schema、跨模組交易）是 `engineering-spec.md`，委派給 `to-engineering-spec`（修訂模式）。以哪一份實際存在於 feature 目錄為準，兩份都在時以 `engineering-spec.md` 為準。**本檔以下一律寫 `engineering-spec.md`，那些敘述對 `issue-doc.md` 同樣成立**——差別只有委派對象與狀態名稱（`定稿` 對應 `final`）。

## 工作流位置

```text
（開發中途發現要改）
  → grill-me / grill-with-docs（使用者自己跑，取得共識）
  → [to-change-request]  ← 本 skill：分流 → 同步 spec → 同步 engineering-spec → 一個確認關卡 → 追加 ticket
  → implement-stepwise
```

它**不是**主線流程的一站。第一次做這個功能時走的是 `to-spec → to-engineering-spec → to-tickets`；本 skill 只服務「已經有 spec、開發到一半、要改」這個情境。

## 為什麼需要這一層

**Matt 原生流程在這裡是斷的。** `to-spec` 只有「把對話 synthesize 成一份 spec 並 publish」一種行為，沒有修訂模式——中途重跑會重寫整份規格。所以 Matt 的中途改動走的是 `grill → implement`，`spec.md` 根本不會同步。原生設計如此並無不妥（Matt 的 spec 是拋棄式的工作稿），但本 plugin 的 `engineering-spec.md` 是**會被就地修訂、且是下游驗收基準的權威**，它必須跟上。

手動補這個斷點要依序跑四支 skill、通過三個確認關卡。本 skill 把中間三支收成一次調用、一個關卡。

**它不重寫任何一支上游 skill。** 分工如下：

| 這一段 | 怎麼做 | 為什麼 |
| --- | --- | --- |
| grill | **不在本 skill 內** | `grill-me` 與 `grill-with-docs` 都是 `disable-model-invocation: true`，model 觸發不到；而且該選哪一支、要 grill 到什麼程度，是使用者的決定 |
| `engineering-spec.md` 的修訂 | **真委派**：調用 `to-engineering-spec`（修訂模式） | 它是本 plugin 自己的 skill，可被 model 調用。委派才不會讓修訂規則分岔成兩份 |
| `spec.md` 的 delta 編輯 | 本 skill 就地做 | `to-spec` 呼叫不到，而且它做的是「重寫整份」，不是本 skill 要的 delta |
| 追加 ticket | 本 skill 就地做，**有上限** | `to-tickets` 呼叫不到，且它是「從頭拆整份 spec、從 `01` 重新編號」。餵 delta 給它會撞號、會重切一整組票 |

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
| **純實作** | 不改任何人看得到的行為、不改設計決策、不改驗證條件。換寫法、抽方法、改變數命名、補防呆、修一個沒寫進規格的 bug | **停手**。明說「不需要動文件」，請使用者直接去 `implement`。**不要為了留紀錄而動文件** |
| **設計層級** | 需求沒變，但落點、契約、資料結構、交易邊界、驗證條件要調整 | 不碰 `spec.md`；委派 `to-engineering-spec` 修訂 |
| **需求層級** | 要不要做、做到什麼程度變了：新增或刪除 user story、範圍進出、行為改變 | `spec.md` 做 delta 編輯，且**通常會連帶**要求 `engineering-spec.md` 同步 |

判不出來時**問使用者，一句話就好**。猜錯的代價不對稱：把需求層級誤判成純實作，`spec.md` 與 `engineering-spec.md` 會從此與實作分岔，而且**沒有任何徵兆**——下游 `to-acceptance-map` 要等到 branch 收尾才會發現驗收基準是錯的。

三類都可能同時出現。以最高層級為準跑完整流程，純實作的部分不進文件。

## 執行流程

### 1. 定位與讀取

依 `.ai/docs/agents/issue-tracker.md` 的慣例定位 feature 目錄（通常 `.ai/.scratch/<feature-slug>/`）。使用者未指定時依當前 git 分支名稱推斷；推斷不出來就停下來問，不要猜。

讀進來：

- `spec.md` —— 需求權威，**必要**。
- `engineering-spec.md` —— 設計與驗證條件的權威（可能不存在，見下方防呆）。
- `issues/` 底下全部 ticket —— 取得最大編號、相依關係、哪些已完成（checkbox 狀態）。
- `.ai/docs/adr/` 中相關的 ADR、`.ai/CONTEXT.md`（術語一律對齊它）。

**三種要先停下來的狀態：**

| 觀察到 | 處置 |
| --- | --- |
| `spec.md` 不存在 | 這條 branch 沒走過 Matt 流程。停手，請使用者跑 `/to-spec`，本 skill 沒有東西可以 delta |
| `engineering-spec.md` 不存在 | 這個功能當初判定不需要正式規格。**不要順手幫他補一份**——那是 `to-engineering-spec` 建立模式的事，而且要先過適用門檻。告知使用者，取得同意後才只做 spec delta 與開票 |
| `engineering-spec.md` 的 `文件狀態` 是 `定稿` | 開發已經收尾過一輪。停下來確認：這是同一條 branch 的續作（確認後把狀態退回 `可拆 Ticket` 再修訂），還是該開新的 feature？**不要在定稿文件上靜默續改** |

### 2. 分流

依上一節判定。純實作 → 回報後停手，流程結束。

### 3. 同步 `spec.md`（僅需求層級改動）

**只做 delta 編輯。** 規範見下方「`spec.md` 的編輯授權」。

### 4. 委派 `to-engineering-spec` 修訂模式

調用該 skill，並明確告知：這是**修訂模式**、改動內容是什麼、`spec.md` 已經（或不需要）同步。它自己會處理權威歸屬、`VC-xx` 的就地改寫、修訂紀錄與送出前自檢——**本 skill 不重述那些規則，也不繞過它直接改 `engineering-spec.md`**。

它停下來要求裁決時（衝突處理、需求層級事實誤入設計文件），**照它的要求把問題轉給使用者，不要代答**。

### 5. 確認關卡（本 skill 唯一的關卡）

把兩份文件的改動一起攤給使用者：

- `spec.md` 改了哪幾段，改成什麼（原文 → 新文）。
- `engineering-spec.md` 改了哪些章節、哪幾條 `VC-xx` 被改寫或刪除。
- **受影響的既有 ticket**：哪些已完成的票所交付的行為被這次改動推翻、哪些未完成的票需要重新理解。
- 準備追加的 ticket 草案（標題、`Blocked by`、交付什麼）。

**未取得使用者確認前不寫任何 ticket 檔案。** 收到修正意見時回到第 3、4 步改完再攤一次。

### 6. 追加 ticket

確認通過後才寫。規範見下方「開票規範」與「上限」。

### 7. 停止並回報

回報：分流結果、兩份文件各改了什麼、新票路徑與編號、受影響的既有票清單。最後給一行可直接貼上的下一步：

```text
$implement-stepwise 依 .ai/.scratch/<feature-slug>/issues/<NN>-<slug>.md
```

**本 skill 不自行調用任何 implement skill。**

## `spec.md` 的編輯授權

`to-engineering-spec` 規定「頂部一行指標是唯一允許對 Matt Spec 做的改動」——**那條規範的對象是 `to-engineering-spec` 自己**，理由是設計文件不該回頭改需求文件的內容。本 skill 的角色不同：它是需求變更的處理者，`spec.md` 的 delta 編輯正是它的職責之一。

授權範圍到此為止，以下是硬規則：

- **只改受本次變更影響的段落。** 沒被影響的一個字都不動，不順手潤稿、不重排章節、不補齊當初就沒寫的東西。
- **不重寫整份、不重新 publish、不改檔名、不另存副本。** 就地改同一份。
- **維持 Matt 的 spec 模板結構**（Problem Statement / Solution / User Stories / Implementation Decisions / Testing Decisions / Out of Scope / Further Notes）。不新增章節、不加欄位。
- **user story 的編號**：新增的接在最後，不插號、不重排；被取消的**改寫或刪除那一條**，不留一條矛盾的舊條文並存。刪除時在 `Out of Scope` 補一句說明它為什麼被拿掉。
- **不在 `spec.md` 加變更紀錄章節。** 變更理由記在 `engineering-spec.md` 的「修訂紀錄」一列，並在該列註明同時改了 `spec.md` 的哪一段——那份文件本來就有這個欄位，兩邊各記一份只會分岔。`engineering-spec.md` 不存在時，靠 git history，不要為此在 `spec.md` 長出一個 Matt 模板沒有的章節。
- **設計事實不要留在 `spec.md`。** 這次 grill 產生的落點、契約、責任歸屬，寫進 `engineering-spec.md`；`spec.md` 的 `Implementation Decisions` 只留需求層級的敘述。兩邊各留一份完整敘述，就是下一次的衝突來源（見 `to-engineering-spec` 的「單邊遺漏」）。

## 開票規範

沿用 Matt `to-tickets` 的 `<local-ticket-template>` **原文格式**，不自訂欄位：

```markdown
# <NN> — <Ticket title>

**What to build:** <從使用者角度描述這張票讓什麼行為成立，不是分層實作清單>

**Blocked by:** <既有票的編號／標題，或 "None — can start immediately">

**Status:** ready-for-agent

- [ ] <驗收條件>
```

規則：

- 寫入 `.ai/.scratch/<feature-slug>/issues/<NN>-<slug>.md`，**編號接在既有最大號之後**，不從 `01` 重編、不插號。
- `Blocked by` 填既有票的編號。已完成的票不必列為 blocker（它已經不 gate 任何東西），除非新票要在它的基礎上改。
- **既有票一律不回頭修改**——不改內容、不改 checkbox、不刪除。它是切片當下的快照，這條規則與 `to-engineering-spec` 定稿模式、`to-acceptance-map` 一致。被推翻的行為靠新票收掉，靠 `engineering-spec.md` 的 `VC-xx` 記錄現行事實。
- ticket 內**不寫檔案路徑與程式碼片段**（Matt 的規則，會很快過期）。
- 不加「本票來自 change request」之類的來源註記欄位。追溯靠 `engineering-spec.md` 的修訂紀錄，不靠在 ticket 上長欄位。
- **不 publish 到任何遠端 tracker。**

## 上限與退場

**追加上限：兩張票，且不得重排既有票的相依順序。**

命中下列任一條就**停手**，不要硬做：

- 需要追加三張以上的票。
- 這次改動推翻了**尚未完成**的既有票，導致相依順序要重排。
- 需要刪除或合併既有票。

這不是保守，是分界：「追加一張票」和「重排一組票」是兩件事。後者需要重算整張相依圖，那本來就是 `to-tickets` 的本體，塞進本 skill 只會養出一套會與它分岔的規則。

退場時，前面的文件同步**照樣做完**（那是本 skill 的價值所在），只在開票這一步停下來，輸出一行給使用者貼：

```text
$to-tickets 依 .ai/.scratch/<feature-slug>/spec.md 與 engineering-spec.md 重拆，既有 issues/ 內容一併帶入
```

## 執行限制

本 skill **不負責**下列事項，出現時停下來導引使用者用對應的 skill：

- 寫程式、跑測試（`implement-stepwise`）。
- review 程式碼（`code-review`）。
- `engineering-spec.md` 的**定稿**（`to-engineering-spec` 定稿模式，發生在整條 branch 收尾時，不是每次改動）。
- 產出交付版（`engineering-spec-deliverable`）、盤點測試覆蓋（`to-acceptance-map`）。
- 建立、更新、留言或關閉任何遠端 Issue。GitLab 維持唯讀。

寫完檔案後停止，**不自行調用下一支 skill**。
