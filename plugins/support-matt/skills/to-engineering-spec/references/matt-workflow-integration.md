# 與 Matt workflow 的銜接

判斷權威順序、檔案位置或與 Matt skill 的介面時讀本文件。

## 各文件的職責

```text
grill-with-docs → to-spec → to-engineering-spec → 人工確認 → to-tickets → implement → code-review → to-engineering-spec（定稿）
```

| 產物 | 誰產 | 是什麼的權威 | **不是**什麼的權威 |
| --- | --- | --- | --- |
| `.ai/CONTEXT.md` | `domain-modeling` | 專案術語 | 需求、設計 |
| `.ai/docs/adr/NNNN-*.md` | `domain-modeling` / `grill-with-docs` | 少量、重要、難以回復且有真實取捨的決策**理由** | 完整設計；ADR 不該長成規格 |
| `.ai/.scratch/<slug>/spec.md` | `to-spec` 建立，`to-change-request` 修訂 | **需求、範圍、行為、user stories、測試決策** | 系統分析、資料表結構、交易邊界、可判斷真偽的驗證條件 |
| `.ai/.scratch/<slug>/engineering-spec.md` | **本 skill** | **系統分析、設計決策、實作約束、驗證條件** | 需求要不要做、做到什麼程度 |
| `.ai/.scratch/<slug>/issues/NN-*.md` | `to-tickets` | 工作切片與其順序 | 需求、架構 |
| 程式碼與測試 | `implement` | 實際落地證據 | 不自動凌駕已確認規格 |
| 公司 GitLab Issue | 人 | 正式的人類紀錄 | 不作為 Agent 的細碎工作佇列 |

**Matt Spec 的 Implementation Decisions 不改變權威歸屬。** 該模板允許 Spec 放 API contracts 與 technical clarifications from the developer，但**設計事實的權威仍在 `engineering-spec.md`**。Spec 裡出現的設計事實有兩種合法狀態：已經被本文件接走（Spec 那處收斂成需求層級），或經判斷後認定它其實是需求層級事實。**兩邊各留一份完整敘述不是解法**——那會製造兩份會分岔的版本。判斷與處置見 `SKILL.md` 的「單邊遺漏」。

## 權威順序（衝突時怎麼判）

1. **需求類事實**（要做什麼、誰用、什麼算完成）→ Matt Spec 勝。本文件跟著改。
2. **設計類事實**（怎麼做、資料長怎樣、邊界在哪）→ 本文件勝。Matt Spec 不該寫這些；若它寫了且與本文件衝突，停下來請使用者決定要不要把那段從 Matt Spec 移除。
3. **決策理由** → ADR 勝。本文件引用 ADR 編號，不複製理由全文。
4. **術語** → `.ai/CONTEXT.md` 勝。兩份文件都必須用它的字。
5. **程式碼** → **不自動勝**。程式碼與規格不一致是一個要被決策的事實，不是一個自動生效的更新。

**任何順位衝突都不由 skill 自行裁決**，一律停下來指出衝突並要求處理（見 SKILL.md 的「衝突處理」）。

## 不重複的實作方式

Matt Spec 已經寫了 user stories、Out of Scope、Testing Decisions。本文件**不重抄**：

| 想寫的東西 | 正確做法 |
| --- | --- |
| 功能要達成什麼 | 一句話帶過 + `見 [spec.md](./spec.md) 的 Problem Statement / Solution` |
| 使用情境清單 | 不重寫 user stories。需要指涉某條時寫 `見 spec.md User Story 12：審核者可退回申請單` |
| 不做什麼 | 「範圍與非範圍」只寫**系統邊界**（哪個模組不動、哪張表不碰）；產品層級的 Out of Scope 引用 Matt Spec |
| 測試在哪個 seam | Matt Spec 的 Testing Decisions 已定案時引用它；未定案時本文件以「實作方向」提出 |
| 驗收基準 | **本文件的「驗證條件」章是權威**，但只寫「怎麼驗證 Matt Spec 那條需求成立」，每條指回 user story、BR 或設計章節。不重寫 user stories、不擴充也不縮減範圍 |

引用一律帶一句摘要，不留裸連結——判準見 `writing-rules.md` 的「刪掉編號測試」。

## 檔案位置

先讀 `.ai/docs/agents/issue-tracker.md` 確認 tracker 設定（由 `setup-matt-preset` 產生）。

本 skill 的 feature 目錄一律寫 `.ai/.scratch/`：`setup-matt-preset` 把 Matt 規範中落在 repo 根目錄的產物整批下移一層，只換層級，命名與存放方式照 Matt 原樣。**實際位置以該 repo 的 `issue-tracker.md` 為準**——未跑過 `setup-matt-preset` 的 repo 仍是根層的 `.scratch/`，此時去掉 `.ai/` 前綴讀寫。

**Local markdown（本專案的預設情境）**——一功能一目錄，spec 為 `.ai/.scratch/<feature-slug>/spec.md`，ticket 為 `.ai/.scratch/<feature-slug>/issues/<NN>-<slug>.md`。本文件併入同一個目錄：

```text
.ai/.scratch/<feature-slug>/
├── spec.md
├── engineering-spec.md
└── issues/
    └── 01-<slug>.md
```

好處是三者相對連結穩定（`./spec.md`、`./issues/01-foo.md`），`code-review` 找 spec 時掃 `.ai/.scratch/` 會一起看到。

`<feature-slug>` **沿用 Matt Spec 建好的目錄名**，不自己另取。目錄不存在時（使用者先跑本 skill）才自行建立，並用同一套 kebab-case slug。

**其他 tracker（GitHub / GitLab / Linear）**——本地沒有 `.ai/.scratch/<feature-slug>/`。與使用者確認落點，建議 `docs/specs/<feature-slug>/engineering-spec.md`，並在「文件資訊」用 Issue 連結取代 `spec.md` 的相對路徑。

## 公司 GitLab 的界線

- 本 skill **不建立、不修改、不留言、不關閉**任何遠端 Issue。不呼叫 `gh issue`，也不呼叫 `glab` 的任何寫入子指令（`issue create` / `update` / `note` / `close` / `reopen` / `delete`、`mr create` 等），不以 `glab api` 發出非 GET 請求。
- 公司 GitLab Issue 可以作為**輸入**（PRD 來源），透過 `glab issue view` 讀取，或使用者直接貼上。
- Matt 的 Spec 與 Tickets 留在 `.ai/.scratch/`，不上 GitLab——這正是 tracker 設成 Local markdown 的目的：避免公司 GitLab 被大量 Agent 工作 Issue 汙染。
- `engineering-spec.md` 由**使用者自己**決定何時貼回公司 GitLab Issue。
- **本文件是工作版，不是交付版。** 它帶著 `./spec.md` 的相對連結、ADR 編號引用與給 `to-tickets` 的 handoff——這三樣在管線裡都是必要的，貼上 Issue 後卻全部失效：Issue 上沒有 `./spec.md`，相對連結是死的，handoff 是內部工作註記。
- 要貼上 Issue 時，由 **`engineering-spec-deliverable`** 產出交付版 `engineering-spec_deliverable.md`（引用改內嵌、handoff 改寫成給人看的解讀規則），原檔不動。本 skill 不做這件事。
- 工作版隨時要成立的只有一件事：**沒有 Agent 對話痕跡、沒有開發過程日誌、沒有內部工作註記**（修訂紀錄一列一句除外）。

## 讓下游穩定讀到本文件

Matt 的 `to-tickets` 只在使用者傳入 reference 時才會 fetch，`implement` 只讀使用者指定的 spec 或 tickets。**單靠產出 handoff 章節不足以保證它們讀得到**——handoff 寫在文件裡，而問題正是它們可能不打開這份文件。

依侵入程度由低到高，三道保險一起上。**都不修改 Matt 的上游 Skill。**

### 1. Matt Spec 頂部的一行指標（必做）

在 `.ai/.scratch/<feature-slug>/spec.md` 最上方（標題之後）加一行：

```markdown
> Engineering spec: [engineering-spec.md](./engineering-spec.md) — 系統分析、設計決策與實作約束的權威。拆票與 review 時一併閱讀；實作以 ticket 為準。
```

這是**本 skill 唯一**允許對 Matt Spec 做的改動：一行指標，不是內容，不與需求權威競爭。任何 skill 只要 fetch 了 spec.md 就會看到它。

需求層級的內容改動由 `to-change-request` 負責（開發中途的再入點：grill 之後同步兩份文件並追加 ticket）。它是 `spec.md` 的合法修訂者，但也只做受影響段落的 delta 編輯，不重寫整份。

### 2. 呼叫時明講兩個路徑（必做）

回報訊息給出可直接貼上的一行：

```text
$to-tickets 依 .ai/.scratch/<feature-slug>/spec.md 與 .ai/.scratch/<feature-slug>/engineering-spec.md 拆票，並參照 docs/adr/ 與 CONTEXT.md
```

`to-tickets` 的 step 1 明說會 fetch 使用者傳入的 reference，這是最直接有效的一道。

### 3. repo-level 的 `## Agent skills` 補充（建議做一次）

`setup-matt-preset` 會把 Matt 原本要寫進 `CLAUDE.md` / `AGENTS.md` 的 `## Agent skills` 區塊內容存成 `.ai/docs/agents/workflow.md`，再於根目錄的 `CLAUDE.md`（與 `AGENTS.md`，若存在）以 `@.ai/docs/agents/workflow.md` 匯入，細節同樣放在 `.ai/docs/agents/*.md`。沿用**同一個擴充點**，不另起爐灶：

在 `.ai/docs/agents/workflow.md` 的 `## Agent skills` 區塊底下補一個子區塊（存在則就地更新，不重複 append）。未跑過 `setup-matt-preset` 的 repo，該區塊仍直接寫在 `CLAUDE.md` / `AGENTS.md` 裡，就改那裡：

```markdown
### Engineering spec

需要正式 SA / SD 的功能，在 `to-spec` 之後、`to-tickets` 之前產出 `.ai/.scratch/<feature>/engineering-spec.md`。拆票與 review 時一併閱讀；實作以 ticket 為準，ticket 不足時才回頭查相關章節。見 `.ai/docs/agents/engineering-spec.md`。
```

並寫 `.ai/docs/agents/engineering-spec.md`：

```markdown
# Engineering spec

需要正式系統分析與設計的功能，除了 `spec.md` 之外還有一份 `engineering-spec.md`，與 spec 同目錄。

- **`spec.md`**：需求、範圍、行為的權威——要不要做、做到什麼程度。
- **`engineering-spec.md`**：系統分析、設計決策、實作約束與**驗證條件**的權威——怎麼驗證它成立。

## 給 to-tickets / implement / code-review 的規則

- 拆票與 review 時兩份都讀。`spec.md` 決定要做什麼，`engineering-spec.md` 決定怎麼做才算沒做錯。
- 實作以 ticket 為準，不主動讀這兩份；ticket 不足時才回頭查相關章節，並回報 ticket 缺了什麼。拆票時已把設計決策帶進 ticket，實作再讀一次只是重複。
- **設計決策**（`> **設計決策**：` 或資料表 / 介面契約 / 交易邊界等章節）是硬約束。要改，先回 `to-engineering-spec` 修訂文件。
- **實作方向**（`> **實作方向**：`）可依 codebase 現況調整，但要在 Ticket 或 PR 記錄原因。靜默偏離視同缺陷。
- **實作示意**（程式碼區塊上方標了「非固定簽章」）不是契約，不要照抄簽章。
- Ticket 採 tracer-bullet vertical slices，不按 Controller / Service / DB 分層拆工。Ticket 不等於單一 commit。
- 兩份文件衝突時停下來問人，不要自己選一邊。
```

**這一步要先問使用者再寫**——它動的是整個 repo 共用的 Agent 設定檔。使用者拒絕時，前兩道保險已經夠用，照常繼續。

## 給 code-review 的銜接

`code-review` 的 Spec axis 會 fetch 「originating spec」。經過上面三道保險，它會同時拿到兩份文件。判斷規則就是 `constraint-levels.md` 最後一節：

- 違反設計決策 → 缺陷。
- 偏離實作方向且有記錄原因 → 不是缺陷；記下來，定稿模式同步進文件。
- 偏離實作方向且無記錄 → 缺陷（靜默偏離）。
- 沒照實作示意 → 不報。

`code-review` 跑完、使用者確認接受結果後，回本 skill 跑**定稿模式**。
