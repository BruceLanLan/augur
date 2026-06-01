中文 | [English](README_EN.md)

<div align="center">

<img src="docs/images/zh/hero-banner.png" alt="Augur" width="100%"/>

# 🦉 Augur

**你的 AI 投资决策委员会**

*18位投资大师，同时分析，一次共识*

[![v8.0.0](https://img.shields.io/badge/v8.0.0-Latest-00d4aa?style=for-the-badge)](https://github.com/BruceLanLan/augur)
[![18 Masters](https://img.shields.io/badge/18-Investment%20Masters-brightgreen?style=for-the-badge)](#-18位投资大师)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude%20%2F%20Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

> **巴菲特会买这只股吗？达利欧怎么看宏观风险？段永平觉得管理层够不够「本分」？**
>
> 真正重要的不是单一视角的分析，而是多维度的共识。Augur 让 **18位** 顶级投资人同时为你分析，每人给出独立评分，最终汇成一个带 Kelly 仓位建议的加权共识信号。

> **🦉 为什么是白色像素猫头鹰？**
> 在日本文化中，白色猫头鹰（フクロウ）是招财和智慧的象征。「フクロウ」的发音可以拆解为「不苦労」（没有辛苦）或「福来郎」（福气到来）。我们用白色像素猫头鹰作为 Augur 的 Logo，寓意：**用 AI 的智慧，让投资决策少一点辛苦，多一点回报。**

---

## 💡 为什么是 Augur？

| 维度 | 传统单策略 | ChatGPT 问答 | **Augur** |
| :--- | :---: | :---: | :---: |
| **分析视角** | 1 种 | 随机/通用 | **18 种独立投资流派** |
| **量化评分** | ✗ | ✗ | **0-10 结构化独立打分** |
| **中国投资人** | ✗ | 有偏见/缺乏深度 | **段永平/张磊/李录/但斌** |
| **实时数据** | 手动输入 | 无/滞后 | **yfinance 自动获取** |
| **仓位建议** | ✗ | ✗ | **Kelly 公式动态计算** |
| **自学习权重** | ✗ | ✗ | **IC 反馈自动优化** |
| **系统集成** | ✗ | ✗ | **MCP Server / Hermes 接入** |

---

## 🧠 18位投资大师

<details>
<summary><strong>经典价值派</strong></summary>

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

## 🚀 30秒上手

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -e ".[data]"

# 分析
augur analyze AAPL                  # 18位大师共识，自动拉取实时数据
augur consensus NVDA                # 加权共识 + Kelly 仓位建议
augur report TSLA                   # 生成深度分析报告

# v8 新功能
augur chat AAPL --persona buffett   # 向巴菲特提问
augur sentiment NVDA                # 社交情绪分析

# 启动 Dashboard
python3 -m dashboard.app            # → 浏览器打开 http://localhost:8000
```

---

## ✨ 真实运行效果

```text
$ augur consensus NVDA

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
    • ⚡ AI revenue rapidly growing, AGI path clear
    • 🚀 Revenue 122%, S-curve early rapid expansion

  BULLISH (11): buffett, fisher, aschenbrenner, cathie_wood, thiel...
  NEUTRAL  (5): dalio, marks, graham, soros, serenity
  BEARISH  (2): arps, munger
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🆕 v8.0.0 新功能

v8 将 Augur 从「分析工具」升级为「智能投资平台」，新增 10 个模块：

### 🖥️ 新增 Dashboard 页面

| 页面 | 入口 | 功能 |
|------|------|------|
| **AI 对话** | `/chat` | 11位大师独特语气回答，无需 LLM API |
| **组合优化** | `/optimizer` | Markowitz 有效前沿，纯 Python 实现 |
| **大师对决** | `/compare` | 选 2-5 位大师对同一股票独立分析对比 |
| **辩论模式** | `/debate` | 多大师顺序辩论，每位回应前者观点 |
| **历史记录** | `/history` | 分析历史持久化，可按股票/时间回查 |
| **大师排行** | `/performance` | 基于 IC 反馈的大师准确率排行榜 |

### 🧠 智能后端增强

| 模块 | 功能 |
|------|------|
| **LearningEngine** | IC 反馈自动调整共识权重（持久化至 `~/.augur/`） |
| **SentimentAnalyzer** | X/Reddit/StockTwits 情绪因子融入共识计算 |
| **WebSocket 实时行情** | `/ws/prices` 实时价格推送，Bloomberg Ticker Tape |
| **RulesEngine** | DSL 条件告警规则，多渠道推送 |

### 🔧 可选高级功能

| 模块 | 启用方式 |
|------|---------|
| 多用户系统（JWT + SQLite） | `AUGUR_MULTI_USER=1` |
| API 认证（Bearer Token） | `AUGUR_API_TOKEN=your_token` |
| 插件系统（第三方 Agent） | setuptools `entry_points` 机制 |

---

## 📊 Bloomberg 风格 Dashboard

```bash
python3 -m dashboard.app --port 8000
```

**17 个页面**，覆盖完整投资分析流程：

| 分组 | 页面 | 功能亮点 |
|------|------|---------|
| **分析** | 仪表盘 | 快速分析入口 + 全球市场行情面板 |
| | 股票分析 | 18位共识 + 评分卡片 + 多空辩论 + 深度报告 |
| | 信号监控 | 自选股批量扫描，60s 自动刷新 |
| | 扫描器 | 预设标的全量评分热图 |
| | 自选股 | 一键分析，localStorage 持久化 |
| | 持仓管理 | 持仓追踪 + 实时盈亏 + 资产配置图 |
| | 历史回测 | IC 排行榜 + 大师命中率 |
| **v8 功能** | AI 对话 | 11位大师对话，有独特语气和观点 |
| | 组合优化 | Markowitz 均值-方差优化 |
| | 大师对决 | 2-5位大师同题独立分析横向对比 |
| | 辩论模式 | 多大师顺序辩论，生成辩论摘要 |
| | 历史记录 | 所有分析历史，可按条件检索 |
| | 大师排行 | IC 加权的大师预测准确率追踪 |
| **投资人** | 人格系统 | 18位大师卡片 + 搜索/流派筛选 |
| | 创建大师 | 无代码 YAML 自定义 persona |
| **系统** | 设置 | 每位大师独立配置参数 |

<p align="center">
  <img src="docs/images/zh/dashboard-preview.png" alt="Augur 仪表盘预览" width="100%"/>
</p>

<p align="center">
  <img src="docs/images/zh/dashboard-stocks.png" alt="股票分析页面" width="100%"/>
</p>

---

## 🔌 多平台部署

<p align="center">
  <img src="docs/images/zh/architecture.png" alt="Augur 系统架构" width="100%"/>
</p>

<p align="center">
  <img src="docs/images/zh/consensus-flow.png" alt="共识决策流程" width="100%"/>
</p>

### Claude Desktop / Hermes（MCP）

```bash
# 安装 MCP 支持（需要 Python 3.10+）
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # 验证可启动
```

**Hermes** (`~/.hermes/config.yaml`):
```yaml
mcp_servers:
  augur:
    command: /path/to/augur/.venv/bin/augur
    args: [mcp-server]
skills:
  external_dirs:
    - /path/to/augur/skills
```

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "augur": {
      "command": "/path/to/augur/.venv/bin/augur",
      "args": ["mcp-server"]
    }
  }
}
```

7 个 MCP 工具：`augur_analyze` · `augur_consensus` · `augur_fetch` · `augur_list_personas` · `augur_configure` · `augur_create_persona` · `augur_debate`

### Telegram / Slack / WeChat / Lark

```bash
pip install -e ".[telegram]" && export TELEGRAM_TOKEN='...' && augur telegram
pip install -e ".[slack]" && export SLACK_BOT_TOKEN='...' SLACK_APP_TOKEN='...' && augur slack
pip install -e ".[wechat]" && augur wechat --mode personal
pip install -e ".[lark]" && export LARK_APP_ID='...' LARK_APP_SECRET='...' && augur lark
```

### Docker

```bash
docker compose up -d dashboard           # http://localhost:8000
docker compose --profile telegram up -d  # + Telegram Bot
```

---

## ⚙️ CLI 命令参考

```bash
# ── 核心分析 ─────────────────────────────────────────────────────────────────
augur analyze AAPL                            # 18位共识，自动获取实时数据
augur analyze NVDA --persona buffett          # 指定单个大师
augur analyze TSLA --persona cathie_wood --json  # JSON 输出（脚本用）
augur consensus AAPL                          # 加权共识 + Kelly 仓位
augur report TSLA                             # 生成深度 Markdown 报告
augur list-personas                           # 列出全部 18 位投资人

# ── v8 新增命令 ──────────────────────────────────────────────────────────────
augur chat AAPL --persona buffett             # 向巴菲特提问
augur chat NVDA                               # 随机大师回答
augur sentiment TSLA                          # 社交情绪分析（X/Reddit/StockTwits）

# ── 数据获取 ─────────────────────────────────────────────────────────────────
augur fetch AAPL                              # 仅获取数据，不分析
augur fetch 0700.HK --json                    # 港股，JSON 格式

# ── 回测与 IC 追踪 ───────────────────────────────────────────────────────────
augur backtest AAPL --days 30 --live          # yfinance 真实历史
augur ic-report                               # 大师准确率排行榜

# ── 自选股监控 ───────────────────────────────────────────────────────────────
augur watchlist-add AAPL --sector Technology
augur watchlist-show
augur cron-run                                # 立即运行监控
augur cron-start                              # 启动定时守护进程

# ── 服务 ─────────────────────────────────────────────────────────────────────
python3 -m dashboard.app --port 8000 --cors   # Dashboard（含完整 API）
augur api --port 8900                         # 轻量 REST API
augur mcp-server                              # MCP Server（stdio）

# ── 平台机器人 ───────────────────────────────────────────────────────────────
augur telegram / augur slack / augur wechat / augur lark
```

**参数单位约定（务必遵守）：**

| 类型 | 单位 | 正确示例 | 错误示例 |
|------|------|---------|---------|
| 利率/利润率/增速 | 小数 (0-1) | `--roe 0.55`（55%） | ~~`--roe 55`~~ |
| 负债率 | 小数 (0-1) | `--debt-ratio 0.35` | ~~`--debt-ratio 35`~~ |
| 机构/内部持股 | 整数百分比 | `--institutional-ownership 66` | ~~`--institutional-ownership 0.66`~~ |
| 市值/FCF | **十亿美元** | `--market-cap 2800`（$2.8T） | ~~`--market-cap 2800000000000`~~ |

---

## 🔧 YAML 自定义投资人

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

保存后 Dashboard 热加载即可生效，CLI 重启后自动注册。

---

## 📡 主要 API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/analyze/{ticker}` | GET | 18位共识，自动拉取数据 |
| `/api/report/{ticker}` | GET | 深度 Markdown 报告 |
| `/api/sentiment/{ticker}` | GET | 社交情绪分析 |
| `/api/chat` | POST | AI 对话（body: message, agent_id） |
| `/api/optimize` | POST | 组合优化（body: tickers, risk_free_rate） |
| `/api/compare` | POST | 大师对决（body: ticker, agent_ids） |
| `/api/debate` | POST | 辩论模式（body: ticker, agent_ids） |
| `/api/history` | GET | 分析历史列表 |
| `/api/rules` | GET/POST | 告警规则管理 |
| `/api/personas` | GET | 列出全部 18 位大师 |
| `/api/watchlist` | GET/POST | 自选股管理 |
| `/ws/prices` | WebSocket | 实时价格推送 |
| `/ws/analyze/{ticker}` | WebSocket | 流式分析进度 |
| `/health` | GET | 健康检查 |

完整 API 文档：[docs/api-reference.md](docs/api-reference.md)

---

## ❓ 常见问题

<details>
<summary>提示 "yfinance not installed"</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server 提示 "No module named mcp"</summary>

`mcp` 包需要 Python 3.10+：
```bash
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server   # 验证可启动
```
</details>

<details>
<summary>分析结果总是 NEUTRAL + 低分</summary>

最常见原因是参数单位错误：
- ✅ `--roe 0.55` (55%)  ❌ ~~`--roe 55`~~
- ✅ `--debt-ratio 0.35`  ❌ ~~`--debt-ratio 35`~~
- ✅ `--market-cap 2800` ($2.8T)  ❌ ~~`--market-cap 2800000000000`~~
</details>

<details>
<summary>pip install 报 "File 'setup.py' not found"</summary>

pip 版本过低，不支持 `pyproject.toml`：
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -e ".[data]"
```
</details>

<details>
<summary>Kelly 仓位显示 0% 或 N/A</summary>

Kelly 只在 BULLISH 信号且评分 > 5 时给出非零建议。NEUTRAL/BEARISH 保守返回 0。
</details>

---

## 📝 版本日志

<details>
<summary><strong>v8.0.0 — 智能投资平台（当前版本）</strong></summary>

- 新增 AI 对话、组合优化、大师对决、辩论模式、历史记录、大师排行 6 个 Dashboard 页面
- LearningEngine：IC 反馈自动调整 18 位大师的共识权重
- SentimentAnalyzer：社交情绪因子融入共识计算
- WebSocket 实时行情推送
- 多用户系统（opt-in）、JWT 认证、插件系统
- 测试数量：653 个（vs v7.8.3 的 ~160 个）
</details>

<details>
<summary><strong>v7.8.x — 视觉重设计 + Bug 修复</strong></summary>

- DQ1 像素风格品牌重设计：白色像素猫头鹰 Logo、18位大师像素头像
- 报告页投票表渲染修复（正则匹配 bug）
- CRCL 分析修复：coverage_confidence 门控防止 AGI 标签污染无关公司
- 加密货币/大宗商品/国债利率面板
- OG 图片路径修复，双语 README
</details>

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
MIT License · Built by <a href="https://github.com/BruceLanLan">BruceLanLan</a>

<em>仅供学习研究，不构成投资建议</em>
</div>
