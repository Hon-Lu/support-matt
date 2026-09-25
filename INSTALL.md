## 安裝教程

### Claude Code 安裝/更新/移除 指令說明
安裝指令 (於終端開啟 Claude Cli 後，依序輸入以下指令)：
```
/plugin marketplace add Hon-Lu/support-matt
```
```
/plugin install support-matt
```
```
/reload-plugins
```

更新指令：
```
/plugin marketplace update support-matt
```
```
/reload-plugins
```

移除指令：
```
/plugin uninstall support-matt
```
```
/plugin marketplace remove support-matt
```

### Codex 安裝/更新/移除 指令說明
安裝指令 (開啟 Command 終端後直接輸入)：
```powershell
codex plugin marketplace add Hon-Lu/support-matt
```
```powershell
codex plugin add support-matt@support-matt
```
更新指令：

```powershell
codex plugin marketplace upgrade support-matt
```
```powershell
codex plugin add support-matt@support-matt
```

移除指令：
```powershell
codex plugin remove support-matt@support-matt
```
```powershell
codex plugin marketplace remove support-matt
```

### 前置需求

本 plugin 掛在 [Matt Pocock 的 skills](https://github.com/mattpocock/skills) 上運作，安裝前請先具備該套 skill。
