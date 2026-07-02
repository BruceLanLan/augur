🇨🇳 中文 | [🇺🇸 English](README_EN.md)

<div align="center">

<img src="docs/images/zh/hero-banner.png" alt="Augur — 你的 AI 投资决策委员会" width="100%">

# 🦉 Augur

**18 位传奇投资人，同时分析同一支股票，给出一个共识裁决。**

把 Warren Buffett、Ray Dalio、段永平、Cathie Wood 放在同一个房间——他们不会同意对方的观点。这正是重点。

[![v10.0.0](https://img.shields.io/badge/v10.0.0-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur/releases)
[![2136 Tests](https://img.shields.io/badge/2136_Tests-Passing-brightgreen?style=for-the-badge)](https://github.com/BruceLanLan/augur/actions)
[![18 大师](https://img.shields.io/badge/18-投资大师-gold?style=for-the-badge)](#-18位投资大师)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude_%2F_Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![PWA](https://img.shields.io/badge/PWA-可安装应用-blue?style=for-the-badge)](#-dashboard-web-界面)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 🚀 30秒上手

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e ".[data]"
augur serve --open          # 打开 Dashboard
```

或者直接在命令行：

```bash
augur analyze AAPL          # 18位大师同时分析
augur consensus NVDA        # 加权共识 + Kelly 仓位建议
augur workflow TSLA         # 一次调用跑完整分析链
```

---

## ✨ v10.0 有什么新的

<img src="docs/images/screenshots/dashboard-hd2d.png" alt="Augur v10 首页 — 实时行情 + Bloomberg 风格终端" width="100%">

### 你的专属 Bloomberg 终端

**`/settings` 页面现在是一个完整的终端配置系统：**

<img src="docs/images/screenshots/workspace-profiles.png" alt="Terminal Workspace — 多套 Profile 保存切换" width="100%">

- **4 套布局预设**：analyst / trader / committee / minimal，一键切换首页和工具栏
- **多套命名 Profile**：保存"白天看盘"和"周末研究"两套配置，互不影响
- **启用大师子集**：只让你信任的几位大师参与共识，权重自动重归一化
- 配置保存在 `~/.augur/workspace.yaml`，换机器也能带走

### AI Agent 现在能操作你的终端

不只是"聊天"——你的 Claude / Hermes Agent 现在可以直接**读取并修改**你的 Augur 工作区：

```python
# Claude Desktop / Hermes 里直接调用：
mcp_augur_workspace_get()                       # 查看当前布局和启用的大师
mcp_augur_workspace_set(layout_preset="trader") # 切换到 trader 模式
mcp_augur_workspace_profiles()                  # 管理你的所有 Profile
```

### 一次调用跑完整分析链

```bash
augur workflow NVDA --steps fetch,analyze,consensus,committee
```

`fetch → analyze → consensus → committee → debate → sentiment` 六步流水线，单步失败不中断，步骤跟随你的 Profile 自动调整。

---

## 📊 Dashboard 全貌

<img src="docs/images/screenshots/personas-hd2d.png" alt="18位投资大师 — 四大流派" width="100%">

### 股票分析

<img src="docs/images/screenshots/report-hd2d.png" alt="股票分析页 — 输入 Ticker 召唤18位大师" width="100%">

输入任意股票代码（A股 / 美股 / 港股），18位大师同时给出：
- **Augur 评分**（0–10）+ **BUY / NEUTRAL / SELL** 信号
- **Kelly 仓位建议**（基于加权共识置信度）
- **The Oracle of Augur**：一句话裁决
- 多空分布：`13 Bullish / 5 Neutral / 0 Bearish`

### 投资委员会

<img src="docs/images/screenshots/committee-hd2d.png" alt="投资委员会 — 预设组合 + 独立意见 + 最终裁决" width="100%">

五套预设委员会，也可以自由组合：
- **经典价值**：Buffett · Graham · Munger · Fisher
- **中国价值**：段永平 · 张磊 · 李录 · 但斌
- **宏观全天候**：Dalio · Soros · Marks · ARPS
- **创新成长**：Cathie Wood · Thiel · Aschenbrenner · Lynch
- **全体委员会**：18位全部出席

### 多空辩论

<img src="docs/images/screenshots/04-bullish-critical.png" alt="结构化辩论 — 多空双方自动交锋" width="100%">

选 2–4 位大师就同一标的展开多轮辩论，自动生成完整的多头和空头论据。

### 历史记录

<img src="docs/images/screenshots/history.png" alt="分析历史 — GitHub 风格热力图 + 详细记录" width="100%">

每次分析自动存档，GitHub 风格 52 周热力图，按信号 / 评分 / 日期筛选。

---

## 🎭 18位投资大师

> 4 大流派，覆盖价值 / 成长 / 宏观 / 中国市场。中国大师**全程中文对话**。

| 流派 | 大师 |
|------|------|
| 🏦 经典价值 | Warren Buffett · Benjamin Graham · Charlie Munger · Philip Fisher |
| 🚀 成长创新 | Peter Lynch · Cathie Wood · Peter Thiel · Leopold Aschenbrenner |
| 🌍 宏观周期 | Ray Dalio · George Soros · Howard Marks · ARPS Crypto/Gold |
| 🇨🇳 中国价值 | 段永平 · 张磊（高瓴）· 李录（喜马拉雅）· 但斌（东方港湾）· 大宇 BTCdayu |
| ⚙️ 特殊策略 | Serenity（AI算力供应链）|

每位大师都有独立的 [Hermes Skill](src/skills/)，可直接在 Hermes Studio 里单独对话。

---

## 🔌 接入任意平台

| 平台 | 接入方式 |
|------|---------|
| **Web Dashboard** | `augur serve` |
| **Claude Desktop** | MCP 配置 → `augur mcp-server` |
| **Hermes Agent** | `/skill augur-buffett` |
| **Claude Code** | `.mcp.json` 自动发现（克隆即用） |
| **OpenClaw** | YAML manifest 自动注册 |
| **Telegram / Slack** | `augur telegram` / `augur slack` |

### MCP 13个工具

```json
// Claude Desktop (~/.config/claude/claude_desktop_config.json)
{
  "mcpServers": {
    "augur": { "command": "augur", "args": ["mcp-server"] }
  }
}
```

| 工具 | 用途 |
|------|------|
| `mcp_augur_analyze` | 单个或全部大师分析 |
| `mcp_augur_consensus` | 加权共识 + Kelly 仓位 |
| `mcp_augur_committee` | 投委会（独立意见 + 裁决） |
| `mcp_augur_debate` | 多轮结构化辩论 |
| `mcp_augur_workflow` | 完整分析流水线 |
| `mcp_augur_workspace_get` | 🆕 读取你的终端配置 |
| `mcp_augur_workspace_set` | 🆕 修改你的终端配置 |
| `mcp_augur_workspace_profiles` | 🆕 管理 Profile |
| `mcp_augur_fetch` | 实时行情 |
| `mcp_augur_sentiment` | 社交情绪分析 |
| `mcp_augur_create_persona` | 创建自定义大师 |
| `mcp_augur_list_personas` | 列出全部大师 |
| `mcp_augur_configure` | 配置模型参数 |

---

## 💻 CLI 完整命令

```bash
# 分析
augur analyze AAPL                              # 18位大师共识
augur analyze AAPL --persona buffett            # 单个大师
augur consensus NVDA                            # 加权共识 + Kelly 仓位
augur workflow TSLA --steps fetch,analyze,consensus,committee

# Dashboard
augur serve --port 8000 --open                  # 启动并自动打开浏览器

# 监控
augur watch AAPL NVDA TSLA                      # 60s 刷新
augur watch NVDA --alert-above 7.5             # 评分超阈值提醒

# 组合
augur portfolio AAPL NVDA TSLA                 # Kelly 配置建议
augur backtest AAPL --days 30                  # 历史回测

# Agent
augur mcp-server                               # 启动 MCP server（stdio）
augur skills                                   # 列出所有 Skill
augur skills --school value                    # 按流派筛选

# Bot
augur telegram / augur slack
```

---

## 🎨 创建专属大师

```bash
# 方式一：Dashboard 无代码构建器
augur serve
# 访问 http://localhost:8000/create-persona

# 方式二：YAML 文件
cat > personas/custom/my_quant.yaml << EOF
agent_id: my_quant
name: "我的量化策略"
philosophy: ["动量", "价值", "低波动"]
scoring_weights:
  momentum: 0.40
  value: 0.35
  safety: 0.25
EOF
augur analyze AAPL --persona my_quant

# 方式三：MCP 工具
mcp_augur_create_persona(yaml_content="agent_id: ...")
```

---

## 📝 更新日志

> 非技术向用户说明见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。

<details open>
<summary><strong>v10.0.0 — 终端工作区 + Agentic 工作流 + 13 MCP 工具 + WebSocket 实时推送 (current)</strong></summary>

**v8 → v10 全面升级要点：**

- 🆕 **Terminal Workspace**：Bloomberg 风格多套 Profile，布局预设，大师子集过滤，委员会预设绑定
- 🆕 **3 个工作区 MCP 工具**：Agent 可读写你的终端配置（`workspace_get/set/profiles`）
- 🆕 **`augur_workflow`**：6 步分析流水线，单步失败不中断，步骤联动 Profile
- 🆕 **WebSocket 实时推送**：`/ws/workspace` 状态广播 + `/ws/workflow` 逐步进度
- 🆕 **augur-terminal 元技能**：Hermes 统一入口，13 工具 + 15 页面 + 4 预设
- 🆕 **Hermes committee.yaml**：委员会主席 Agent 角色
- ✅ 共识引擎：行业权重 · regime 路由 · MetaModel · 点时基本面
- ✅ Dashboard：4 语言 i18n · 历史热力图 · PWA · 键盘快捷键 · CSV 导出
- ✅ 2136 个测试全部通过
</details>

<details>
<summary><strong>v10.16.x — 内部迭代（已全部包含在 v10.0.0 中）</strong></summary>

- v10.16.7：历史热力图 + Optimizer Sharpe 修复
- v10.16.6：投委会事件循环阻塞缓解
- v10.16.5：首页 11 个接口阻塞修复
- v10.16.4：投委会 Kelly 仓位显示修复
- v10.16.3：workflow 步骤联动布局预设
- v10.16.2：workflow 局部失败容错 + 工作区 ETag
- v10.16.1：MCP 工作区工具 + 委员会预设接线
</details>

<details>
<summary><strong>v9.0.x — Hermes Agent + 委员会体系</strong></summary>

- 19 个 Hermes Skill，中国大师全中文对话
- 9 个 MCP 工具（committee / sentiment / create_persona / debate）
- 委员会预设系统 + Hermes 接入指南页
- PWA 可安装 + Ticker Tape WebSocket + Chat 数据卡片
</details>

<details>
<summary><strong>v8.2.x — HD-2D 设计系统 + Optimizer + AI 对话</strong></summary>

- Markowitz 有效前沿图 · Rules→Bot 推送 · AI 对话 LLM 支持
- HD-2D 设计系统：ExecCard / OracleSays / ScorecardGrid
- WCAG AA 合规 · 线程安全 · Scanner 加固
</details>

---

<div align="center">

MIT License · Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a>

*仅供学习研究，不构成投资建议*

</div>
