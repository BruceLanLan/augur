[English](README_EN.md) | 中文

<div align="center">

<img src="docs/images/hero-banner-baoyu.svg" alt="Augur" width="100%"/>

# 🦉 Augur

**你的 AI 投资决策委员会**

*18位投资大师，同时分析，一次共识*

[![v6.1.0](https://img.shields.io/badge/v6.1.0-Latest-00d4aa?style=for-the-badge)](https://github.com/BruceLanLan/augur)
[![18 Masters](https://img.shields.io/badge/18-Investment%20Masters-brightgreen?style=for-the-badge)](#18位投资大师)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude%20%2F%20Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

> **巴菲特会买这只股吗？达利欧怎么看宏观风险？段永平觉得管理层够不够「本分」？**
>
> 别再一个维度猜了。Augur 让 **18位** 顶级投资人同时为你分析，每人给出独立评分，最终汇成一个带 Kelly 仓位建议的加权共识信号。

---

## ✨ 真实运行效果

```
$ augur analyze NVDA

Auto-fetching data for NVDA from yfinance...
  Price: 820.00 | PE: 45.0 | ROE: 65.0% | GM: 78.0%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NVDA — 18 Masters Consensus
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Signal:     BULLISH
  Score:      7.6 / 10
  Confidence: 82%
  Kelly Size: 9.2%

  Key Findings:
    • 🛡️ AI reinforcing moat, competitive advantage expanding
    • ⚡ AI revenue rapidly growing, clear AGI commercialisation
    • 🚀 Revenue 122%, S-curve early rapid expansion phase

  BULLISH (11): buffett, fisher, aschenbrenner, cathie_wood, thiel...
  NEUTRAL  (5): dalio, marks, graham, soros, serenity
  BEARISH  (2): arps, munger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🚀 30秒上手

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e ".[data]"

augur analyze AAPL         # 一键分析，自动获取实时数据
augur consensus NVDA       # 18位共识 + Kelly仓位
python3 -m dashboard.app   # 启动 Bloomberg 风格 Dashboard
# → 浏览器打开 http://localhost:8000
```

---

## 💡 为什么是 Augur？

| | 传统单策略 | ChatGPT 问答 | **Augur** |
|--|:--:|:--:|:--:|
| 分析维度 | 1 种 | 随机 | **18 种独立视角** |
| 量化评分 | ✗ | ✗ | **0-10 结构化评分** |
| 中国投资人 | ✗ | 有偏见 | **段永平/张磊/李录/但斌** |
| 实时数据 | 手动输 | 无 | **yfinance 自动** |
| 仓位建议 | ✗ | ✗ | **Kelly 公式** |
| 部署到 Claude/Hermes | ✗ | ✗ | **MCP Server** |

---

## 🧠 18位投资大师

<details>
<summary><strong>经典价值派</strong>（点击展开）</summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🏆 **巴菲特** | 护城河 + 可预测盈利 + FCF | 消费/金融蓝筹 |
| 📐 **格雷厄姆** | 安全边际 PE<15 PB<1.5 | 深度价值股 |
| 🧠 **芒格** | 格栅思维 + 逆向 | 被市场误解的企业 |
| 🔬 **费雪** | Scuttlebutt + 毛利率持续性 | 成长型高质量公司 |

</details>

<details>
<summary><strong>成长与创新</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🚀 **彼得林奇** | PEG < 1.5 + 日常可理解 | GARP 成长股 |
| 💡 **凯西伍德** | Wright定律 + TAM扩张 | AI/基因组/区块链 |
| 🏢 **彼得蒂尔** | 0→1 垄断 + 逆向思考 | 科技平台/深科技 |
| 🤖 **阿申布伦纳** | AGI基础设施 + 算力稀缺 | AI/半导体 |

</details>

<details>
<summary><strong>宏观与周期</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🌐 **达利欧** | 全天候 + 债务周期 | 宏观轮动 |
| 🔄 **索罗斯** | 反射性 + 趋势自我强化 | 趋势交易 |
| 📉 **霍华德马克斯** | 钟摆情绪 + 二阶思考 | 周期底部 |
| 🥇 **ARPS** | 实际利率 + Crypto/黄金 | 通胀对冲 |

</details>

<details>
<summary><strong>🇨🇳 中国投资人（独家）</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🎯 **段永平** | 本分 + 极度集中 | 商业模式清晰的消费科技 |
| 🌏 **张磊（高瓴）** | 结构性长期价值 | 中国成长赛道 |
| 🏔️ **李录（喜马拉雅）** | 深度价值 + 安全边际 | 港股/A股低估值 |
| 🫖 **但斌（东方港湾）** | 品牌护城河 + 时代Beta | 消费龙头 |
| ₿ **大宇（BTCdayu）** | 信息差 + 情绪动量 | Crypto/加密赛道 |

</details>

<details>
<summary><strong>前沿特殊策略</strong></summary>

| 投资人 | 核心框架 | 最强场景 |
|--------|---------|---------|
| 🔭 **Serenity** | AI/半导体供应链瓶颈 | 卡脖子环节标的 |

</details>

---

## 📊 Dashboard

```bash
python3 -m dashboard.app --port 8000 --cors
```

Bloomberg Terminal 风格，**7个页面**，完整分析流程：

| 页面 | 功能 | 亮点 |
|------|------|------|
| **首页** | 快速分析 + 历史记录 | 键盘 `/` 快速聚焦 |
| **股票分析** | 18位共识 + 详情展开 | yfinance 自动填充 |
| **人格系统** | 18位大师卡片 + 搜索/过滤 | 展开看评分权重 |
| **信号监控** | 自选股批量扫描 | 自动 60s 刷新 |
| **历史回测** | IC 排行榜 + 命中率 | 评估大师准确率 |
| **设置** | 每位大师独立配置模型 | 实时保存 |
| **创建大师** | 无代码 YAML 自定义 | 即时注册生效 |

<p align="center">
  <img src="docs/images/dashboard-stocks.svg" alt="Stock Analysis Dashboard" width="100%"/>
</p>

---

## 🔌 多平台部署

### Claude Desktop / Hermes (MCP)

```bash
# Step 1: 安装 MCP 支持 (需要 Python 3.10+)
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # 验证可启动
```

**Hermes** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: /绝对路径/augur/.venv/bin/augur
    args: [mcp-server]

skills:
  external_dirs:
    - /绝对路径/augur/skills    # 启用 /skill augur-buffett 等命令
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": {
      "command": "/绝对路径/augur/.venv/bin/augur",
      "args": ["mcp-server"]
    }
  }
}
```

7个 MCP 工具：`augur_analyze` · `augur_consensus` · `augur_fetch` · `augur_list_personas` · `augur_configure` · `augur_create_persona` · `augur_debate`

> 所有工具均支持**自动实时数据**：不传指标时自动从 yfinance 获取。

### Telegram / Slack / 微信 / 飞书

```bash
# Telegram
pip install -e ".[telegram]"
export TELEGRAM_TOKEN='your-token'
augur telegram

# Slack
pip install -e ".[slack]"
export SLACK_BOT_TOKEN='xoxb-...' SLACK_APP_TOKEN='xapp-...'
augur slack

# 个人微信 (GeWeChat)
pip install -e ".[wechat]"
augur wechat --mode personal

# 飞书
pip install -e ".[lark]"
export LARK_APP_ID='...' LARK_APP_SECRET='...'
augur lark
```

### Docker

```bash
docker compose up -d dashboard          # http://localhost:8000
docker compose --profile telegram up -d  # + Telegram Bot
```

---

## ⚙️ 完整 CLI（17 个命令）

```bash
# ── 核心分析 ──────────────────────────────────────────────────────────────────
augur analyze AAPL                            # 自动实时数据，18位同时分析
augur analyze NVDA --persona buffett          # 仅用巴菲特框架
augur analyze TSLA --persona cathie_wood --json  # JSON 输出（脚本集成）
augur consensus AAPL                          # 18位加权共识 + Kelly 仓位建议
augur consensus NVDA --json                   # JSON 输出（含个体结果）
augur list-personas                           # 列出所有 18 位投资人

# ── 数据 ──────────────────────────────────────────────────────────────────────
augur fetch 0700.HK                           # 仅获取实时数据（不分析）
augur fetch AAPL --json                       # JSON 格式输出

# ── 回测与 IC 追踪 ────────────────────────────────────────────────────────────
augur backtest AAPL --days 30 --live         # 用真实 yfinance 历史数据
augur backtest AAPL --demo                   # 用模拟数据（快速演示）
augur ic-report                              # Agent 预测准确率排行榜

# ── 自选股监控 ────────────────────────────────────────────────────────────────
augur watchlist-add AAPL --roe 0.55 --gross-margins 0.46 --sector Technology
augur watchlist-show                         # 查看当前自选股列表
augur cron-run                               # 立即运行一次自选股分析
augur cron-start                             # 启动定时守护（工作日 09:00 AM）

# ── 服务启动 ──────────────────────────────────────────────────────────────────
python3 -m dashboard.app --port 8000 --cors  # Bloomberg Dashboard（含完整 API）
augur api --port 8900                        # 轻量 REST API
augur mcp-server                             # MCP Server (stdio, 需 Python 3.10+)

# ── Hermes / Claude 集成 ──────────────────────────────────────────────────────
augur inject-soul --persona buffett -f hermes --profile my-buffett
# → 生成 soul.md 并存入 --output-dir（默认当前目录）

# ── 平台 Bot（需先安装对应 extra） ────────────────────────────────────────────
augur telegram    # pip install -e ".[telegram]" && export TELEGRAM_TOKEN=...
augur slack       # pip install -e ".[slack]" && export SLACK_BOT_TOKEN=... SLACK_APP_TOKEN=...
augur wechat      # pip install -e ".[wechat]"  （个人微信 GeWeChat 模式）
augur wechat --mode wecom    # 企业微信
augur lark        # pip install -e ".[lark]" && export LARK_APP_ID=... LARK_APP_SECRET=...
```

**参数约定（所有命令统一）：**

| 参数类型 | 单位 | 正确示例 | 错误示例 |
|---------|------|---------|---------|
| 利润率 / 增速 / 比率 | 小数（0-1） | `--roe 0.55`（55%） | ~~`--roe 55`~~ |
| 资产负债率 | 小数（0-1） | `--debt-ratio 0.35`（35%） | ~~`--debt-ratio 35`~~ |
| 持仓比例 | 整数百分比 | `--institutional-ownership 66`（66%） | ~~`--institutional-ownership 0.66`~~ |
| 市值 / FCF | **十亿 USD** | `--market-cap 2800`（$2.8T）`--fcf 90`（$90B） | ~~`--market-cap 2800000000000`~~ |

---

## 🏗️ 架构

```
augur/
├── src/augur/
│   ├── personas/           # 18位投资人 Python 引擎
│   │   ├── buffett.py … serenity.py   # 每位独立评分逻辑
│   │   └── base.py         # BaseAgent / MarketContext / AgentResponse
│   ├── coordinator.py      # DecisionCoordinator — 6层加权共识
│   ├── registry.py         # AgentRegistry + half-Kelly 仓位计算
│   ├── data.py             # yfinance 实时数据（自动单位换算）
│   ├── mcp_server.py       # MCP Server (7工具, stdio)
│   ├── cli.py              # Click CLI (20命令)
│   ├── api.py              # 轻量 REST API (FastAPI)
│   ├── backtest.py         # IC 回测框架 + leaderboard
│   ├── cron.py             # 定时分析 + watchlist 管理
│   ├── config.py           # 配置管理（线程安全 RLock）
│   ├── soul.py             # Hermes/Claude soul 注入
│   └── bots/               # Telegram / Slack / WeChat / Lark
├── dashboard/              # Bloomberg 风格 Web UI
│   ├── app.py              # FastAPI + 25+ API 路由
│   └── templates/          # 7个页面（含 create-persona / backtest）
├── skills/                 # Hermes/Claude Skill 定义
│   └── buffett/SKILL.md    # 每位大师独立 Skill
├── personas/               # 深度人格文档 + YAML 自定义
├── config/agents.yaml      # Agent 模型配置
├── Dockerfile + docker-compose.yml
└── pyproject.toml          # 包配置 (augur-agents)
```

**共识引擎 6 层加权：**

```
输入指标 → [18位大师独立分析]
         → 行业感知权重    # 科技股 ↑ Wood/Aschenbrenner
         → 市场机制路由    # 熊市 ↑ Marks/Dalio
         → 滚动 IC 权重   # 历史准确率高者动态加权
         → 多样性惩罚     # 观点相似者减少冗余
         → Kelly 仓位     # 置信度 × 信号强度 → 仓位 %
         → 风险否决层     # 高负债+熊市可否决看多
         → 最终共识信号 + 仓位建议
```

---

## 🔧 YAML 自定义大师

无需写 Python，YAML 文件即可创建自定义投资策略：

```yaml
# personas/custom/my_quant.yaml
agent_id: my_quant
name: "我的量化策略"
philosophy: ["动量", "价值", "低波动"]
scoring_weights:
  momentum: 0.40
  value:    0.35
  safety:   0.25
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 55 and rsi < 75", add: 2}
      - {if: "macd > macd_signal",     add: 1}
      - {if: "price > sma50",          add: 1}
  value:
    base: 5
    rules:
      - {if: "pe > 0 and pe < 15",     add: 3}
      - {if: "pb < 1.5 and pb > 0",   add: 2}
  safety:
    base: 5
    rules:
      - {if: "debt_ratio < 0.3",       add: 2}
      - {if: "current_ratio > 2",      add: 2}
```

保存后立即生效，`augur list-personas` 可见。

---

## 📡 Dashboard API 端点

Dashboard 启动后（`python3 -m dashboard.app --port 8000`）自动提供以下 API：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analyze/{ticker}` | GET | 18位共识分析，无指标时自动 yfinance |
| `/api/fetch/{ticker}` | GET | 仅获取实时行情，不分析 |
| `/api/personas` | GET | 列出所有 18 位投资人 |
| `/api/persona/{id}` | GET | 单投资人详情 |
| `/api/config` | GET/PUT | 全局配置读写 |
| `/api/config/persona/{id}` | GET/PUT | 单投资人模型配置 |
| `/api/models` | GET | 可用模型列表 |
| `/api/watchlist` | GET | 自选股列表 |
| `/api/watchlist/add` | POST | 添加自选股 |
| `/api/watchlist/{ticker}` | DELETE | 移除自选股 |
| `/api/watchlist/run` | POST | 批量分析自选股，保存历史信号 |
| `/api/custom-persona` | POST | 创建 YAML 自定义投资人（热加载）|
| `/api/backtest/run` | GET | 运行 IC 历史回测 |
| `/api/backtest/leaderboard` | GET | IC 排行榜 |
| `/api/search` | GET | 股票代码搜索 |
| `/health` | GET | 健康检查 |

---

## ❓ 常见问题

<details>
<summary>augur analyze 报错 "yfinance not installed"</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server 报错 "No module named mcp"</summary>

mcp 包需要 Python 3.10+：
```bash
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # 验证可启动
# 然后在 ~/.hermes/config.yaml 中用绝对路径注册
```
</details>

<details>
<summary>分析结果总是 NEUTRAL，评分偏低</summary>

检查参数单位是否正确（这是最常见的错误）：
- ✅ `--roe 0.55`（55%）  ❌ ~~`--roe 55`~~
- ✅ `--debt-ratio 0.35`（35%）  ❌ ~~`--debt-ratio 35`~~
- ✅ `--market-cap 2800`（$2.8T）  ❌ ~~`--market-cap 2800000000000`~~
- ✅ `--gross-margins 0.46`（46%）  ❌ ~~`--gross-margins 46`~~
</details>

<details>
<summary>Dashboard 页面不显示或 "加载中" 卡住</summary>

```bash
# 1. 检查服务是否正常
curl http://localhost:8000/health   # 应返回 {"status":"ok","agents":18}

# 2. 确认 yfinance 已安装（自动数据获取）
pip install -e ".[data]"

# 3. 启用 CORS（供前端调用）
python3 -m dashboard.app --port 8000 --cors
```
</details>

<details>
<summary>Telegram Bot 发 /analyze AAPL 返回 NEUTRAL（全零数据）</summary>

需要安装 yfinance：
```bash
pip install -e ".[data,telegram]"
# Bot 在无指标时会自动从 yfinance 获取实时数据
```
</details>

<details>
<summary>Kelly 仓位建议显示 0% 或 N/A</summary>

Kelly 只在 BULLISH 信号且 score > 5 时给出非零建议。NEUTRAL/BEARISH 信号下，Kelly 保守返回 0。
</details>

<details>
<summary>自定义 YAML Persona 创建后不出现</summary>

Dashboard 已支持热加载（保存 YAML 后同一进程立即可用）。CLI/API 重启后自动加载 `personas/custom/*.yaml`。
</details>

---

## 🤝 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)，包含：新增投资人（YAML/Python）、修复 Bug、Dashboard 开发、Bot 开发、参数约定等完整指南。

- **新投资人** → `personas/custom/` 放 YAML，或仿 `src/augur/personas/buffett.py` 写 Python
- **算法优化** → 改进 `src/augur/coordinator.py` 共识机制
- **新平台 Bot** → 在 `src/augur/bots/` 添加，参考 `telegram_bot.py`
- **Web UI** → 完善 `dashboard/`，CSS 变量见 `bloomberg.css`

---

## 📈 Star History

<a href="https://star-history.com/#BruceLanLan/augur&Timeline">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=BruceLanLan/augur&type=Timeline" />
 </picture>
</a>

---

<div align="center">

MIT License · Built by [BruceLanLan](https://github.com/BruceLanLan)

*📌 仅供学习研究，不构成投资建议*

</div>
