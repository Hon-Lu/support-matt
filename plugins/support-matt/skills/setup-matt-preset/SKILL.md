---
name: setup-matt-preset
description: 以個人慣例初始化 Matt Pocock skills 的 per-repo 設定。承接 Matt 的 setup-matt-pocock-skills 流程，但預先套用三項固定慣例：一律使用 local markdown issue tracker（GitLab 只讀不寫，經 glab CLI）、所有根層產物改放 .ai/ 下一層、Matt 原本要寫進 CLAUDE.md 的 Agent skills 區塊改存為 .ai/docs/agents/workflow.md 並在 CLAUDE.md（及 AGENTS.md，若存在）以 @ 匯入；另補一段 Matt 沒有的測試情境確認：探索測試專案的分層方式，現行「以測試專案為單位」的跑測試規則不合用時（例如單一測試專案混放單元與整合測試、全跑很久），與使用者討論後寫出 .ai/docs/agents/testing.md，供 implement-stepwise 與 to-acceptance-map 改用該 repo 的執行單位。當使用者要在新專案初始化 Matt workflow，或要替已初始化的 repo 補上測試情境時使用，取代直接調用 setup-matt-pocock-skills。
---

# setup-matt-preset

初始化 Matt Pocock skills 的 per-repo 設定，並自動套用個人慣例。

本 skill **不重寫** Matt 的初始化邏輯。它在執行時讀取 Matt 的 `setup-matt-pocock-skills`，照它的流程走，只是把下列覆寫規則疊上去，再補一段 Matt 沒有的測試情境確認（新增 D）——這樣 Matt 那邊改版時，本 skill 不會過期。

## 為什麼需要這一層

Matt 的 `setup-matt-pocock-skills` frontmatter 有 `disable-model-invocation: true`，**無法由 model 觸發**，只能由使用者手動輸入斜線指令。因此本 skill 採取「讀取並執行」而非「呼叫」：把它的 SKILL.md 與 seed template 當成待執行的規格讀進來，就地執行。

## 執行流程

### 1. 定位 Matt 的初始化 skill

依序尋找 `setup-matt-pocock-skills` 的所在目錄：

1. `~/.claude/skills/setup-matt-pocock-skills/`
2. `~/.claude/plugins/cache/**/skills/setup-matt-pocock-skills/`
3. 專案內 `.claude/skills/setup-matt-pocock-skills/`

找不到就**停下來**告知使用者 Matt 的 skills 尚未安裝，不要自行從零產生設定檔。

找到後讀取該目錄的 `SKILL.md`，以及流程會用到的 seed template（至少 `issue-tracker-local.md` 與 `domain.md`；`triage-labels.md` 僅在 `triage` skill 已安裝時需要）。

### 2. 照 Matt 的流程執行，並套用下列覆寫

完整依照 Matt `SKILL.md` 的 Process 執行（探索 → 呈現發現並詢問 → 確認草稿 → 寫入 → 完成），但以本節覆寫取代對應段落。**未被覆寫的部分一律照 Matt 原樣**，包含步驟 3 的「先給使用者看草稿、讓他修改後才寫入」——那是人工確認關卡，不得省略。

#### 覆寫 A — Issue tracker（取代 Matt 的 Section A）

**不詢問，直接採用 local markdown**，即使 `git remote` 指向 GitHub 或 GitLab。使用 `issue-tracker-local.md` 這份 seed template。

在寫出的 `issue-tracker.md` 末尾補上一段 GitLab 唯讀規則：

```markdown
## GitLab issue（唯讀）

本 repo 的 issue tracker 是上述 local markdown。當使用者另外提供 GitLab issue 作為需求來源時：

- **只可讀取**：以 `glab` CLI 取得 issue 內容與討論串，例如 `glab issue view <number>`、`glab issue view <number> --comments`、`glab issue list`。
- **不可寫入**：不得執行 `glab issue create` / `update` / `note` / `close` / `reopen` / `delete`，也不得以 `glab api` 發出任何非 GET 請求。
- 所有產出一律寫回本地 markdown，不上 GitLab。

建議 glab 使用的 Personal Access Token 只給 `read_api` scope，讓唯讀在 token 層級就成立，不必只靠上述規則。
```

#### 覆寫 B — 所有根層產物下移一層到 `.ai/`

Matt 規範中放在 repo 根目錄的檔案與資料夾，一律改放到 `.ai/` 之下。**只換層級，資料夾命名、檔案命名、存放方式完全照 Matt 的規範**：

| Matt 原路徑 | 本 preset 路徑 |
| --- | --- |
| `.scratch/<feature>/` | `.ai/.scratch/<feature>/` |
| `docs/agents/issue-tracker.md` | `.ai/docs/agents/issue-tracker.md` |
| `docs/agents/domain.md` | `.ai/docs/agents/domain.md` |
| `docs/agents/triage-labels.md` | `.ai/docs/agents/triage-labels.md` |
| `docs/adr/` | `.ai/docs/adr/` |
| `CONTEXT.md`（根層那份） | `.ai/CONTEXT.md` |
| `CONTEXT-MAP.md` | `.ai/CONTEXT-MAP.md` |

**這條最容易漏的地方：seed template 的正文裡也寫滿了路徑。** `issue-tracker-local.md` 通篇引用 `.scratch/...`，`domain.md` 引用 `CONTEXT.md`、`docs/adr/` 並畫了目錄樹。寫出檔案時，**必須把 template 內文的每一處路徑一併改寫**，否則下游 skill 讀到的仍是舊路徑，整套設定等於沒生效。改寫後請自行複查一遍：寫出的檔案內不應再出現任何不帶 `.ai/` 前綴的 `.scratch/`、`docs/agents/`、`docs/adr/`、根層 `CONTEXT.md` 或 `CONTEXT-MAP.md`。

**例外**：上表搬移的一律是**落在專案根目錄**的產物。multi-context 佈局中位於 `src/` 底下的 context 專屬檔案——`src/<context>/CONTEXT.md` 與 `src/<context>/docs/adr/`——**維持原位不動**，它們刻意貼著程式碼放。若使用者希望連這些也搬，會另行說明。

#### 覆寫 C — CLAUDE.md 改為 `@` 匯入

Matt 步驟 4 是把 `## Agent skills` 區塊直接寫進 `CLAUDE.md` 或 `AGENTS.md`。改為：

1. 把該區塊的**內容**寫成獨立檔案 `.ai/docs/agents/workflow.md`（區塊內引用的三個路徑同樣要套用覆寫 B）。
2. 在專案根目錄的 `CLAUDE.md` 補上一行匯入：

   ```markdown
   @.ai/docs/agents/workflow.md
   ```

3. **若 `AGENTS.md` 也存在，同一行一併補上。** 這一點刻意偏離 Matt 步驟 4 的「二選一、不得同時寫入」規則——兩份都存在時兩份都要補。
4. 若 `CLAUDE.md` 與 `AGENTS.md` 皆不存在，建立 `CLAUDE.md` 並寫入該匯入行（Matt 原本要求詢問使用者選哪一個；本 preset 已指定 `CLAUDE.md`）。

已存在該匯入行時不要重複追加。補上匯入行以外，不改動 `CLAUDE.md` / `AGENTS.md` 的其他內容。

#### 新增 D — 測試情境（Matt 沒有對應段落）

`implement-stepwise` 與 `to-acceptance-map` 預設以**測試專案**為跑測試的單位：逐 commit 與收尾只跑受影響的測試專案，全跑留給 branch 結束。這在「單元、整合測試各自一個專案」的 repo 剛好合用；但單一測試專案混放多種測試時，「受影響的測試專案」就等於每張票全跑。本段在初始化時確認這個 repo 屬於哪一種，只在預設不合用時寫出 `.ai/docs/agents/testing.md` 覆寫它。**沒有這份檔案的 repo，下游 skill 一律照預設執行。**

流程與 A–C 相同：探索 → 呈現發現並詢問 → 確認草稿 → 寫入。

**探索**（只看結構，不執行測試）：

- 有哪些測試專案、各用什麼測試框架、怎麼建置。
- 每個專案的測試是否同一層級：只用測試替身的單元測試，與連真實資料庫、HTTP host、瀏覽器的測試，是否混在同一個專案。
- 是否有作用於整個測試組件的全域 setup（例如 NUnit `SetUpFixture`、xUnit collection fixture）會啟動環境——有的話，連單元測試也要付這筆固定成本。
- 專案是否已宣告測試指令（`CLAUDE.md`／`AGENTS.md`、建置或涵蓋率腳本），以及那些指令實際跑的範圍。

**呈現發現並詢問**，依探索結果二選一：

- **各專案已依層級分開** → 說明預設合用，推薦不寫 `testing.md`。只問一句：全跑耗時或環境前置條件要不要記下來？要就只寫那兩段，不要就整段略過。
- **預設不合用**（單一專案混放、或全域 setup 讓任何執行都很貴）→ 明講「照預設，這個 repo 每張票都會全跑」，再與使用者討論：執行單位要縮到什麼（測試類別、檔案、命名空間、package）、怎麼縮（該工具的 filter 寫法）、受影響範圍怎麼界定、哪些測試會寫外部狀態、全跑大概多久、全跑前要不要一律先問。全跑耗時與環境前置條件探索不出來，一律問使用者，不要估。

**`testing.md` 的格式**——只寫需要覆寫預設的段落，不適用的整段省略，不寫「無」：

```markdown
# Testing

本 repo 的測試情境，供 `implement-stepwise` 與 `to-acceptance-map` 讀取。沒寫到的部分照 skill 預設執行。

## 執行單位

以<測試類別>為單位，不以測試專案為單位（<理由，例如單一專案混放單元與整合測試>）。

- 建置：<指令>
- 縮小範圍：<指令，例如 `dotnet test ./Xxx.Tests --no-build --filter "FullyQualifiedName~<類別>"`>
- 受影響範圍：直接對應的測試<類別>，加上引用到被改程式碼的測試<類別>

## 層級對應

- 便宜層（不寫外部狀態）：<路徑或命名空間>
- 昂貴層（寫入資料庫、檔案等外部狀態）：<路徑或命名空間>

## 全跑

約 <N> 分鐘。<超出受影響範圍的執行一律先問使用者。>

## 環境前置

- <例如需要安裝的工具、組件、服務>
```

寫入 `testing.md` 時，`workflow.md` 一併補上這一段；沒寫就不補：

```markdown
### Testing

Test run unit, affected scope and full-run cost for this repo. See `.ai/docs/agents/testing.md`.
```

**專案既有的測試宣告與 `testing.md` 不一致時**（例如 `CLAUDE.md` 指定的腳本會全跑），只在完成回報中點出、建議改成指向 `testing.md`，**不改 `CLAUDE.md`／`AGENTS.md`**——與覆寫 C「匯入行以外不動」一致，那些宣告可能有 CI 或其他成員依賴。

#### 沿用 Matt 原樣的部分

- **Section B（triage 標籤）**：照 Matt 的規則——`triage` skill 未安裝就整段跳過，已安裝則沿用五個預設標籤。
- **Section C（domain docs）**：照 Matt 的規則——預設 single-context，僅在探索到 monorepo 訊號時才詢問 multi-context。路徑套用覆寫 B。

### 3. 完成回報

除了 Matt 步驟 5 的完成訊息之外，額外列出：

- 實際寫出的檔案完整路徑清單（讓使用者一眼確認全部落在 `.ai/` 下）。
- `CLAUDE.md` / `AGENTS.md` 各自是否已補上匯入行。
- 新增 D 的結論：寫了 `testing.md`（覆寫了哪幾段），或判定預設合用而未寫；以及專案既有測試宣告與它不一致之處（若有）。

## 執行限制

- 本 skill 只做 per-repo 設定初始化，**不建立任何 issue、spec 或 ticket**，也不修改任何功能程式碼。
- 找不到 Matt 的 skills 時停止，不自行從零產生設定檔——那會產出與 Matt 規範不同步的內容。
- 重複執行時，就地更新既有設定檔，不重複追加區塊。
- 使用者只要求補上或更新測試情境時（例如已初始化的 repo），**只執行新增 D**，不重跑 A–C、不重問已確定的設定；`workflow.md` 只補 `### Testing` 一段。
