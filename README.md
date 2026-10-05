# support-matt

套件版本：`v0.22.0`
更新時間：2026-10-05
安裝教程：[INSTALL.md](./INSTALL.md)
<!-- 版本對齊 plugins/support-matt/.claude-plugin/plugin.json 與 .codex-plugin/plugin.json，發版時三處版本與此處日期一併更新 -->

---

## 介紹

> [!NOTE]
> 目前 Plugin 僅支持 **Claude Code** 與 **Codex** 安裝

強化 [Matt Pocock 的 skills](https://github.com/mattpocock/skills)，提供更完整的落地開發工作流與規格文件生成。

本 plugin 不取代 Matt 的任何 skill，需搭配該套 skill 使用。

## 目前收錄的 skill

| Skill | 用途 |
| --- | --- |
| `setup-matt-preset` | 以個人慣例初始化 Matt skills 的 per-repo 設定：local issue tracker（GitLab 只讀不寫）、產物一律放 `.ai/`、`CLAUDE.md` 改以 `@` 匯入。取代直接調用 `setup-matt-pocock-skills`。 |
| `to-issue-doc` | 貼上主 Issue 的 `issue-doc.md`，**分兩個時點寫**：拆票前的 brief 只寫「約束」——目標與範圍、方案輪廓、關鍵決策、驗證條件 `VC-xx`、風險（不先定版，這些決策會發生在拆票裡而沒有紀錄），只有 VC 那張表要逐條確認；系統分析、資料模型、介面與流程屬於「紀錄」，留到 branch 做完跑 `final`，由既成事實（程式碼、ticket 核對表、`git diff`）補齊。開發中途就地修訂。 |
| `to-engineering-spec` | 同一種文件，但**動工前一次寫到位**：系統分析、技術設計、實作約束都在拆票前定版、經審查後才動手。差別不在誰的規則比較嚴，而在設計要不要先成為「被遵守的約束」——動角色權限、動 schema 牽動交易邊界、改變既有架構假設，或公司要求動工前提交完整設計時，事後補寫就來不及了。 |
| `engineering-spec-deliverable` | 把工作版 `engineering-spec.md` 轉成可獨立閱讀、可直接貼上公司 GitLab Issue 的交付版。 |
| `implement-stepwise` | 取代 `implement`（**即時插手**）：單一 session 做完整張票，形狀貼近原生，但開場先評估規模、每個 commit 送出前停下附完整 commit message 與變更清單等你過目，回「繼續」才提交並接著做下一個；最後一個 commit 提交後直接跑驗證（測試 + 跨層重複檢查 + 逐條判定驗收條件），做完停在定稿前停點給你看結果；**不自動跑 `code-review`**，只在 ticket 有硬約束可對照、實作偏離計畫或動到高風險區域時於停點建議，你要求才執行；最後才把核對結果寫回 ticket。不預先產 commit checklist。 |
| `to-acceptance-map` | branch 開發完畢後於**獨立 session** 盤點測試覆蓋，產出 `acceptance-map.md`。驗證基準只認規格文件的 `VC-xx`，不拿 ticket 充數。四級判定區分「需補測試」與「不適用測試」，另檢出可能已失效的測試與潛在重複覆蓋（只偵測、不動測試）。回報只呈現例外，全程唯讀。 |
| `to-change-request` | 開發中途改動的**再入點**：grill 完接這一支，一次做完 `spec.md` delta、規格文件修訂（委派給該 feature 實際用的 `to-issue-doc` 或 `to-engineering-spec`）與未完成 ticket 的修訂，一個確認關卡；每份產物改或不改都附理由。需要新票時給出插入票號（如 `04a`）交給 `to-tickets`，已完成的票不動。純實作的改動直接請你去 implement，不動文件。 |

掛載位置：

```
[setup-matt-preset]  ← 每個 repo 第一次使用前跑一次

grill-with-docs → to-spec ─┬─ 設計後補　 → [to-issue-doc brief] → VC 逐條確認 ──┬─→ to-tickets
                           │                                                   │
                           └─ 設計先定版 → [to-engineering-spec] → 人工確認 ────┘
                                          └─ [engineering-spec-deliverable] 隨時可跑
                                                                          ↓
                          單張 ticket，每個 commit 送出前停 → [implement-stepwise]
                                                                          ↓
                                                              整條 branch 的 ticket 全部完成（以下開新 session）
                                                                          ↓
        設計後補　：[to-issue-doc final]（補齊交付內容）→ [to-acceptance-map]
        設計先定版：[to-acceptance-map] → [to-engineering-spec 定稿]

開發中途要改：grill-me / grill-with-docs → [to-change-request] → implement-stepwise
              （文件同步由 to-change-request 委派給這個 feature 實際用的那一份：to-issue-doc 或 to-engineering-spec 的修訂模式）
```

`implement-stepwise` 取代 Matt 的 `implement`，內部調用其 `tdd`，開場先評估 ticket 規模、過重時建議你回 `to-tickets` 拆小，每個 commit 送出前停下讓你過目（附完整 commit message），收尾驗證完先停下給你看結果再寫回 ticket——**不自動跑 `code-review`**，只在命中條件時建議、你要求才執行。不想在 commit 送出前插手時，直接用 Matt 原生的 `implement` 即可，本 plugin 不另外提供不停的版本。

實作規範由四份 reference 提供（`plugins/support-matt/references/`），`implement-stepwise` 依階段各讀一次：

| Reference | 內容 |
| --- | --- |
| `token-discipline.md` | 探索優先序（圖譜優先）、三條防呆、回合數成本 |
| `implementation-rules.md` | TDD 三條覆寫、程式碼與註解規範、commit 格式、邊做邊記 |
| `testing-rules.md` | 測試層級（入場規則與成本歸屬）、Test Consolidation、重跑範圍 |
| `wrap-up-rules.md` | 收尾的驗證、跨層重複檢查、驗收條件判定、定稿前停點、冷眼審查的建議條件與執行、寫回 ticket |

其中 **Test Consolidation** 是為了壓住 TDD 的測試膨脹：GREEN 之後、commit 之前檢視本次新增或修改的測試，把只為取得 RED/GREEN 回饋而生的暫時性測試、重複的 observable behavior 覆蓋、可參數化的同質 cases，以及沒有保護不同風險的跨層級重複併掉或刪掉，讓每個 commit 直接帶進值得長期保留的那一份，**不留 `test: remove redundant tests` 這種收尾 commit**。驗收條件與測試**不要求 1:1**，要成立的是覆蓋的可追溯性。跨 ticket 才浮現的重複由 `to-acceptance-map` 偵測回報，屬於例外的 branch 層 cleanup。

它的上游是**測試層級的入場規則**：整合／UI 測試只用於單元測試無法真正驗證的部分，決定 seam 時就先拿要斷言的旗標／欄位名回便宜層搜尋，能在便宜層完整覆蓋的行為不進昂貴層——測試寫完之後再改層級就是重寫。判準在昂貴層一律**以 case 數計**（一支參數化測試帶 N 列就算 N 次真實環境往返），因為併成參數化只省維護成本、一秒執行時間都不省；已參數化的測試繼續加列時，逐列說不出獨立的保護對象就不加。

## 待補

後續規劃中的 skill 與流程調整尚未定案，確定後補上。
