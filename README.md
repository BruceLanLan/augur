🇨🇳 中文 | [🇺🇸 English](README_EN.md)

<div align="center">

<img src="docs/images/zh/hero-banner.png" alt="Augur — 你的 AI 投资决策委员会" width="100%">

# 🦉 Augur

**你的 AI 投资决策委员会**

*18位传奇投资人，同时分析，一次共识*

[![v9.0.6](https://img.shields.io/badge/v9.0.6-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur/releases)
[![1652 Tests](https://img.shields.io/badge/1652_Tests-Passing-brightgreen?style=for-the-badge)](https://github.com/BruceLanLan/augur/actions)
[![18 大师](https://img.shields.io/badge/18-投资大师-gold?style=for-the-badge)](#-18位投资大师)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude_%2F_Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![PWA](https://img.shields.io/badge/PWA-可安装应用-blue?style=for-the-badge)](#-dashboard-web-界面)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 为什么选择 Augur？

| | 单一策略 / ChatGPT | **Augur** |
|---|---|---|
| 分析视角 | 1种 | **18种**（价值 / 成长 / 宏观 / 中国派） |
| 量化评分 | ❌ | ✅ 0–10分 + Kelly仓位建议 |
| 多空辩论 | ❌ | ✅ 内置 Bull/Bear 对决 |
| 投资委员会 | ❌ | ✅ 可配置预设委员会 |
| 实时行情 | ❌ | ✅ yfinance 自动拉取 |
| AI 对话 | 通用回答 | ✅ 大师人格化对话 + 行情数据卡片 |
| 组合优化 | ❌ | ✅ Markowitz 有效前沿 |
| 多平台接入 | ❌ | ✅ Dashboard / MCP / CLI / Bot |
| 高度 DIY | ❌ | ✅ YAML 无代码创建专属大师 |
| 独立安装 | ❌ | ✅ PWA 可安装为桌面/手机应用 |

---

## 🎭 18位投资大师

### 经典价值派

| 大师 | 核心框架 | 代表问题 |
|------|---------|---------|
| Warren Buffett | 护城河 · 长期持有 · ROE | 这家公司五年后还有竞争优势吗？ |
| Benjamin Graham | 安全边际 · 深度价值 · P/B | 现在的价格比内在价值低多少？ |
| Charlie Munger | 格栅思维 · 逆向 · 反脆弱 | 我们会在哪里犯错？ |
| Philip Fisher | 闲聊法 · 成长质量 · 管理层 | 这家公司有没有在积极研发？ |

### 成长与创新派

| 大师 | 核心框架 | 代表问题 |
|------|---------|---------|
| Peter Lynch | GARP · PEG · 身边机会 | 这个 PEG 是否低于 1？ |
| Cathie Wood | 颠覆创新 · Wright定律 · AI | 五年后这个市场会有多大？ |
| Peter Thiel | 0→1 垄断 · 秘密 · 反共识 | 这家公司有没有别人不知道的东西？ |
| Leopold Aschenbrenner | AGI基础设施 · 地缘 · 算力 | AI算力瓶颈在哪里？ |

### 宏观与周期派

| 大师 | 核心框架 | 代表问题 |
|------|---------|---------|
| Ray Dalio | 全天候 · 债务周期 · 相关性 | 这个资产在滞胀时表现如何？ |
| George Soros | 反身性 · 宏观交易 · 汇率 | 市场的自我强化机制是什么？ |
| Howard Marks | 钟摆情绪 · 二阶思考 | 大多数人怎么看这个？ |
| ARPS | 实际利率 · 黄金 · Crypto | 通胀调整后收益率是多少？ |

### 🇨🇳 中国价值派（全中文对话）

| 大师 | 核心框架 | 代表问题 |
|------|---------|---------|
| 段永平 | 本分 · 极度集中 · 逆向 | 这家公司的商业本质是什么？ |
| 张磊（高瓴） | 结构性长期价值 · 赋能 | 这家公司能做到100年吗？ |
| 李录（喜马拉雅） | 深度价值 · 安全边际 · A股 | 内在价值是否被严重低估？ |
| 但斌（东方港湾） | 品牌护城河 · 时代Beta | 这是不是时代最好的公司之一？ |
| 大宇 BTCdayu | 信息差 · 情绪动量 · Crypto | 市场情绪处于哪个阶段？ |

### 特殊策略

| 大师 | 核心框架 |
|------|---------|
| Serenity | AI供应链瓶颈 · 算力依赖分析 |

---

## 🚀 30秒上手

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e ".[data]"

# 18位大师同时分析 AAPL
augur analyze AAPL

# 加权共识 + Kelly 仓位建议
augur consensus NVDA

# 启动 Web 仪表盘
augur serve --open
```

---

## 📊 Dashboard（Web 界面）

<img src="docs/images/screenshots/dashboard-hd2d.png" alt="Augur Dashboard — 召唤18位大师" width="100%">

Bloomberg 终端 × JRPG HD-2D 美学。输入 Ticker，18位大师同时开始分析。

```bash
augur serve              # 默认 http://localhost:8000
augur serve --port 8080  # 自定义端口
docker compose up        # Docker 一键启动
```

安装为独立应用（PWA）：浏览器访问后点击地址栏"安装"按钮，即可像本地应用一样使用。

### 股票分析页

<img src="docs/images/screenshots/report-hd2d.png" alt="股票深度分析 — NVDA BUY 7.6分" width="100%">

实时抓取市值、PE、ROE、FCF 等数据，18位大师独立评分后合并共识。输出：
- **Augur 评分**（0–10）+ **BUY / NEUTRAL / SELL**
- **置信度** + **Kelly 仓位建议**
- **The Oracle of Augur**：一句话共识裁决
- **13 Bullish / 5 Neutral / 0 Bearish**：多空分布

### 多空辩论

<img src="docs/images/screenshots/04-bullish-critical.png" alt="Bull/Bear 深度分析" width="100%">

自动生成多头与空头的完整论据，帮助发现盲点。

### 投资委员会

选择任意大师组合，召开委员会会议，每位大师独立发言后自动生成裁决，并记录在历史中。

预设委员会：**经典价值** · **中国价值** · **宏观全天候** · **创新成长** · **全体委员会**

### 人格大师页

<img src="docs/images/screenshots/personas-hd2d.png" alt="18位投资大师" width="100%">

### 历史记录

<img src="docs/images/screenshots/history.png" alt="分析历史记录" width="100%">

每次分析自动存档，可按时间、评分、信号筛选回溯。

### 全部页面

Dashboard / 股票分析 / 信号 / 扫描 / 自选股 / 持仓 / 回测 / AI对话 / 组合优化 / **投资委员会** / 对决 / 辩论 / 历史 / 排行 / 大师 / 创建大师 / Hermes接入指南 / 设置

---

## 🔌 接入任意平台

<img src="docs/images/screenshots/05-available-everywhere.png" alt="一键部署到任意平台" width="100%">

| 平台 | 接入方式 |
|------|---------|
| **Web Dashboard** | `augur serve` — 内置 FastAPI + 无配置 |
| **Claude Desktop** | MCP 配置 → `augur-mcp` 命令 |
| **Hermes Agent** | `/skill augur-buffett` 直接对话 |
| **OpenClaw** | YAML manifest 自动注册 |
| **Telegram / Slack** | `augur telegram` / `augur slack` |
| **Claude Code / Codex** | `.mcp.json` 自动发现 |

### MCP 快速配置

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": { "command": "augur", "args": ["mcp-server"] }
  }
}
```

**Hermes Studio** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: augur
    args: [mcp-server]
```

### MCP 工具（9个）

| 工具 | 用途 |
|------|------|
| `mcp_augur_analyze` | 单个或全部大师分析 |
| `mcp_augur_consensus` | 加权共识 + Kelly 仓位 |
| `mcp_augur_committee` | 投资委员会（独立意见+裁决） |
| `mcp_augur_debate` | 多轮结构化辩论 |
| `mcp_augur_fetch` | 实时行情数据（yfinance） |
| `mcp_augur_sentiment` | 社交情绪分析（StockTwits + 新闻） |
| `mcp_augur_list_personas` | 列出全部18位大师 |
| `mcp_augur_configure` | 配置大师模型参数 |
| `mcp_augur_create_persona` | 无代码创建自定义大师 |

---

## 💻 CLI 命令

```bash
# 分析
augur analyze AAPL                      # 18位大师共识
augur analyze AAPL --persona buffett    # 单个大师
augur consensus NVDA                    # 加权共识 + Kelly 仓位
augur report TSLA                       # 生成深度 Markdown 分析报告

# 实时监控
augur serve --port 8000 --open          # 启动 Dashboard，自动打开浏览器
augur watch AAPL NVDA TSLA             # 实时监控（60s 刷新）
augur watch NVDA --alert-above 7.5     # 评分超阈值时提醒

# 组合管理
augur portfolio AAPL NVDA TSLA         # Kelly 组合配置建议
augur watchlist-add AAPL               # 添加到自选股
augur backtest AAPL --days 30          # 历史回测

# Agent / MCP
augur mcp-server                       # 启动 MCP server（stdio，供 Claude/Hermes 接入）
augur skills                           # 列出所有 Agent Skill
augur skills --school value            # 按流派筛选

# Bot 推送
augur telegram                         # 启动 Telegram Bot
augur slack                            # 启动 Slack Bot
```

---

## 🎨 高度 DIY — 创建专属大师

```bash
# 方式一：Dashboard 无代码构建器（推荐）
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

## 📝 版本日志

<details>
<summary><strong>v9.0.6 — PWA 可安装独立应用 (current)</strong></summary>

- **PWA 支持**：Dashboard 可作为独立应用安装到桌面或手机，离线缓存核心界面。
- **Ticker Tape**：首页顶部实时价格滚动条（WebSocket 驱动，支持暂停/断线重连）。
- **Chat 数据卡片**：AI对话页顶部嵌入实时行情卡，Augur 共识信号 60 秒自动刷新。
</details>

<details>
<summary><strong>v9.0.x — Hermes Agent + 委员会体系</strong></summary>

- **19个专属 Hermes Skill**：每位大师有完整人格化 system prompt，中国大师全中文对话。
- **9个 MCP 工具**：新增 committee / sentiment / create_persona / debate。
- **委员会预设**：一键加载经典价值 / 中国价值 / 宏观全天候 / 创新成长 / 全体委员会。
- **Hermes 接入指南页**（`/hermes-setup`）：分步骤集成说明，代码一键复制。
- **.mcp.json 自动发现**：Claude Code / 任意 MCP 客户端自动找到所有工具。
- **`augur serve / watch / skills / portfolio` CLI**：完整命令行工具集。
- **install.sh 一键安装脚本**，Docker v9，Makefile v2。
</details>

<details>
<summary><strong>v8.2.x — Optimizer + Rules→Bot + AI 对话</strong></summary>

- **Optimizer 有效前沿图**：Markowitz 散点+折线图，金色星标最优组合点。
- **Rules→Bot 打通**：规则满足时自动推送 Telegram / Slack / WeChat / Lark 通知。
- **AI 对话升级**：支持真实 LLM（claude-opus-4-8），多轮历史，⚡LLM / 📋模板 徽章。
- **Scanner 加固**：大小写不敏感去重，单 ticker 失败不阻断批量扫描。
- **后端线程安全**：double-checked locking，原子写 history，`_write_lock`。
- **WCAG AA 对比度合规**，CSS 变量全面替换硬编码颜色。
</details>

<details>
<summary><strong>v8.2.0 — HD-2D 设计系统全面上线</strong></summary>

- AI Chat（11位大师对话）、Portfolio Optimizer、Committee、Debate、History、Leaderboard 全部上线。
- LearningEngine（IC自动调权）、SentimentAnalyzer（社交情绪融合）。
- WebSocket 实时价格推流 `/ws/prices`，RulesEngine DSL 多通道告警。
- HD-2D 设计系统：ExecCard / OracleSays / ScorecardGrid 组件，响应式断点，双语数字格式。
</details>

---

<div align="center">

MIT License · Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a>

*仅供学习研究，不构成投资建议*

</div>
