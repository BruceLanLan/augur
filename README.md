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

## ⚙️ 完整 CLI

```bash
# 核心分析
augur analyze AAPL                     # 自动实时数据，18位分析
augur analyze TSLA --persona cathie_wood  # 指定大师
augur consensus NVDA                   # 加权共识 + Kelly仓位
augur list-personas                    # 列出所有投资人

# 数据与回测
augur fetch 0700.HK --json            # 仅获取市场数据
augur backtest AAPL --days 30 --live  # 真实历史回测
augur ic-report                       # Agent IC 准确率排行

# 自选股监控
augur watchlist-add AAPL --pe 32 --roe 0.55 --gross-margins 0.46
augur cron-run    # 立即运行一次
augur cron-start  # 启动定时守护（工作日 9:00）

# Hermes Soul 注入
augur inject-soul --profile buffett-profile --persona buffett -f hermes
```

**参数约定：**

| 参数类型 | 单位 | 示例 |
|---------|------|------|
| 比率/利润率 | 小数 | `--roe 0.55` = 55% |
| 持仓比例 | 整数百分比 | `--institutional-ownership 66` = 66% |
| 市值/FCF | 十亿 USD (B) | `--market-cap 2800` = $2.8T |

---

## 🏗️ 架构

```
augur/
├── src/augur/
│   ├── personas/           # 18位投资人 Python 引擎
│   │   ├── buffett.py      #   护城河评分逻辑
│   │   ├── serenity.py     #   AI/半导体供应链
│   │   └── ... (18个)
│   ├── coordinator.py      # 共识引擎（6层加权）
│   ├── data.py             # yfinance 实时数据
│   ├── mcp_server.py       # MCP Server (6工具)
│   ├── cli.py              # Click CLI (15+命令)
│   ├── backtest.py         # IC 回测框架
│   ├── cron.py             # 定时分析
│   └── bots/               # Telegram/Slack/WeChat/Lark
├── dashboard/              # Bloomberg 风格 Web UI
│   ├── app.py              # FastAPI + 全部路由
│   └── templates/          # 7个页面模板
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

## ❓ 常见问题

<details>
<summary>augur analyze 报 "yfinance not installed"</summary>

```bash
pip install -e ".[data]"
```
</details>

<details>
<summary>MCP Server 启动失败 "No module named mcp"</summary>

mcp 包需要 Python 3.10+：
```bash
uv venv --python 3.11 .venv
uv pip install -e ".[mcp]"
.venv/bin/augur mcp-server
```
</details>

<details>
<summary>分析结果总是 NEUTRAL</summary>

检查参数单位：毛利率/ROE 用小数（`--roe 0.55` 不是 `--roe 55`），市值用亿（`--market-cap 2800` = $2.8T）
</details>

<details>
<summary>Dashboard 显示 "加载中" 不动</summary>

确认 yfinance 已安装 + 后端正常运行：
```bash
curl http://localhost:8000/health  # 应返回 {"status":"ok","agents":18}
```
</details>

---

## 🤝 贡献

- **新投资人** → `personas/custom/` 放 YAML，或仿 `src/augur/personas/buffett.py` 写 Python
- **算法优化** → 改进 `src/augur/coordinator.py` 共识机制
- **新平台 Bot** → 在 `src/augur/bots/` 添加
- **Web UI** → 完善 `dashboard/` 前端

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
