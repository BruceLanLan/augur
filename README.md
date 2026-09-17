🇨🇳 中文 | [🇺🇸 English](README_EN.md)

<div align="center">

<img src="docs/images/zh/hero-banner.png" alt="Augur — Research Memory System" width="100%">

# 🦉 Augur

**不是又一个 AI 荐股工具。是一个帮你记住"你何时知道什么、什么变了、谁在什么事实上分歧"的本地研究记忆系统。**

[![v11.0.0-rc1](https://img.shields.io/badge/v11.0.0--rc1-Release_Candidate-ff6b35?style=for-the-badge)](CHANGELOG.md)
[![Tests](https://img.shields.io/github/actions/workflow/status/BruceLanLan/augur/tests.yml?branch=main&label=tests&style=for-the-badge)](https://github.com/BruceLanLan/augur/actions/workflows/tests.yml)
[![18 大师](https://img.shields.io/badge/18-投资大师-gold?style=for-the-badge)](#-18-位投资大师)
[![MCP](https://img.shields.io/badge/MCP-1.x_%2F_2.x-orange?style=for-the-badge)](#-接入-claude--agent)
[![Local-First](https://img.shields.io/badge/Local--First_🔒-blue?style=for-the-badge)](#-数据与隐私)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

> ⚠️ **仅供学习研究，不构成投资建议。** 大师观点是基于公开投资理念的规则化模拟，不代表本人立场；所有分数、Kelly 仓位与估值都依赖数据质量和模型假设。

---

## 🤔 为什么 Augur 不一样

大多数 AI 金融工具给你一个答案。Augur 给你的是**可复查的研究产物**。

| | 普通 AI 工具 | Augur |
|---|---|---|
| 给你什么 | 一段"一方面…另一方面…" | 18 位大师的独立判断 + 他们在哪里一致、在哪里打架 |
| 数据从哪来 | 不清楚 | 每条证据带来源、业务时点、可得时点、获取时点 |
| 缺失数据 | 静默填 0 | 显式标注 `missing`，依赖该字段的大师 `abstain` 并说明原因 |
| 三个月后回头看 | 不记得上次说了什么 | 每次运行存为不可变的 RunBundle，可以导出、比较、复查 |
| 数据在哪 | 云端 | 本地 `~/.augur`（可用 `AUGUR_DATA_DIR` 改），无遥测 |

---

## 🚀 5 分钟上手

需要 Python 3.9+（MCP 功能需要 3.10+）。

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[data]"            # 核心 + yfinance 实时数据
# 可选：pip install -e ".[data,mcp]"  MCP server
#       pip install -e ".[export]"    PDF 导出

# SEC EDGAR 要求请求里带真实联系邮箱（用于美股财报数据）
export AUGUR_EDGAR_CONTACT_EMAIL="you@example.com"
```

**Dashboard：**

```bash
augur serve --open                 # http://localhost:8000 · ⌘K 命令面板
```

**命令行研究闭环**（以下命令均在全新安装上实测通过）：

```bash
augur analyze AAPL                 # 18 位大师同时分析 + 加权共识 + Kelly 仓位
augur workflow AAPL                # 带追踪的流水线，保存 RunBundle，末尾打印 Run ID
augur research-report AAPL         # 基于最近一次运行：共识、分歧图、来源信息
augur export AAPL --format md      # 导出最近一次运行（md / json / evidence-pack / pdf）
augur committee AAPL --preset value -q "护城河是在变宽还是变窄？"
augur valuation AAPL               # 两阶段 DCF，自动取 FCF/股本/净负债并注明来源
```

没有网络？`augur analyze NVDA --pe 60 --roe 0.45` 可以手动传指标；`augur backtest AAPL --demo` 使用离线合成数据。

---

## 🔄 从 v10 升级

公开仓上一个版本是 v10.15.0。v11 是一次**可信度与研究底座**升级，不是新增大师或新页面。升级前请注意这些行为变化：

| 变化 | 影响 | 如何处理 |
|---|---|---|
| `insider_ownership` / `institutional_ownership` 从 `0` 变为 `Optional[float]` | 缺失时是 `None`，依赖它们的 11 位大师会 abstain | 自定义代码里处理 `None` |
| rolling-IC 权重默认不混入共识 | 只有校准状态为 `validated-calibrated` 才生效 | 实验时设 `AUGUR_FORCE_RIC=1` |
| 学习权重（R6）默认不混入共识 | 数据太少时会把噪声当能力 | 实验时设 `AUGUR_FORCE_LEARNED=1` |
| SEC EDGAR 市值单位修正为十亿美元 | 此前覆盖层返回美元原值，市值/FCF 收益率相关判断失真；**v11 之前基于回放生成的因子/IC 结果含该误差** | 需要时重新生成回放产物 |
| `augur serve` / `augur api` 默认只监听 `127.0.0.1` | 局域网默认不可访问 | 对外暴露前先设 `AUGUR_API_TOKEN`，再加 `--host 0.0.0.0` |
| 旧格式回放记录（无 `field_availability`）会被拒绝 | 给出明确报错，而不是静默加载 | 重新生成 |
| Python 最低版本 3.9；MCP 支持 `mcp` 1.x 与 2.x | — | — |

完整说明见 [docs/RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md) 与 [CHANGELOG.md](CHANGELOG.md)。

---

## 🎭 18 位投资大师

> 规则化实现的投资理念画像，覆盖价值 / 成长 / 宏观 / 中国市场。中国大师输出中文。

| 流派 | 大师 |
|------|------|
| 🏦 经典价值 | Warren Buffett · Benjamin Graham · Charlie Munger · Philip Fisher |
| 🚀 成长创新 | Peter Lynch · Cathie Wood · Peter Thiel · Leopold Aschenbrenner |
| 🌍 宏观周期 | Ray Dalio · George Soros · Howard Marks · ARPS（加密/黄金） |
| 🇨🇳 中国价值 | 段永平 · 张磊 · 李录 · 但斌 · 大宇 |
| ⚙️ 特殊策略 | Serenity（AI 算力供应链） |

共识引擎按置信度、数据覆盖度和行业相关性加权，给出信号、分数、置信度和 Kelly 仓位建议。`augur list-personas` 查看全部 ID。

<img src="docs/images/screenshots/personas-hd2d.png" alt="18 位投资大师" width="100%">

---

## 📊 Dashboard

`augur serve` 启动后访问 http://localhost:8000。

| 页面 | 路径 | 功能 |
|---|---|---|
| 首页 | `/` | 行情 + 大师概览 |
| 股票分析 | `/stocks` | 输入 ticker，18 位大师同时分析 |
| 投资委员会 / 辩论 / 对比 | `/committee` · `/debate` · `/compare` | 预设委员会、多轮辩论、五维雷达图 |
| 历史 | `/history` | 运行历史与热力图 |
| Thesis Journal | `/thesis` | 投资论文、证伪条件、决策日志 |
| 财报 | `/earnings` · `/scorecard` | 财报事件队列、事后记分卡 |
| 研究收件箱 | `/inbox` | 聚合待处理事件 |
| 估值实验室 | `/valuation` | DCF 参数表单 + 敏感度网格 |
| 组合 / 自选 / 设置 | `/portfolio` · `/watchlist` · `/settings` | Kelly 配置、定时分析、布局与大师子集 |

---

## 🔌 接入 Claude / Agent

MCP server 提供 13 个工具、7 个研究 prompt、5 类只读资源（`augur://evidence/{id}`、`augur://runs/{id}`、`augur://thesis/{id}`、`augur://decisions/{id}`、`augur://ledger/{ticker}/{quarter}`），在 `mcp` 1.x 与 2.x 下都经过真实 stdio 会话验证。

```bash
pip install -e ".[data,mcp]"
```

Claude Desktop 配置示例：

```json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp", "env": { "AUGUR_EDGAR_CONTACT_EMAIL": "you@example.com" } }
  }
}
```

另有 Hermes / OpenClaw 技能包（`src/skills/`，见 [docs/hermes-setup-guide.md](docs/hermes-setup-guide.md)）以及 Telegram / Slack / 飞书 / 微信机器人入口。

---

## 💻 CLI 速查

```bash
# 分析
augur analyze AAPL [--persona buffett] [--json]
augur workflow TSLA --steps fetch,analyze,consensus,committee,debate,sentiment
augur committee NVDA --agents buffett,munger,dalio
augur batch AAPL MSFT NVDA

# 研究产物
augur research-report AAPL [--format json]
augur export AAPL --format md|json|evidence-pack|pdf [-o 路径] [--run-id ...]
augur dossier AAPL                  # 财报前 dossier
augur valuation AAPL [--fcf 100e9 --shares 15e9 --growth 0.08 --wacc 0.10]
augur filing-delta AAPL --new q3.json --prev q2.json

# 数据
augur fetch AAPL · augur sentiment AAPL · augur insider AAPL · augur earnings --days 30
augur backtest AAPL --days 60 [--demo] · augur ic-report · augur doctor

# 监控与服务
augur watch AAPL NVDA --interval 60 · augur watchlist-add AAPL · augur cron-run
augur serve [--port 8000] · augur mcp-server · augur skills
```

`augur --help` 列出全部 39 个子命令。

---

## 🧭 功能成熟度

如实标注，避免把"有代码"当成"能用"。

| 状态 | 范围 |
|---|---|
| **稳定** | 18 位大师分析与共识、CLI 研究闭环（上面实测过的命令）、Dashboard 主要页面、MCP server、RunBundle 与导出、数据源链（yfinance → SEC EDGAR 覆盖） |
| **可用但有限制** | 分歧图的"冲突点"是按信号分布套用模板生成的通用表述，不是逐条证据推导；`augur guidance` 需要设 `AUGUR_EDGAR_GUIDANCE_EXTRACTION=1` 且会调用付费 LLM；PDF 导出需要 `[export]` 额外依赖 |
| **实验（默认关闭）** | rolling-IC 动态权重（`AUGUR_FORCE_RIC=1`）、学习权重（`AUGUR_FORCE_LEARNED=1`）——都还没有通过预注册的样本外验证 |
| **仅库代码，尚无用户入口** | `citation_queue`、`cost_budget`、`eval_lab`、`outcome_tracker`、`pack_digest`、`prompt_eval`、`review_comment`、`risk_review`、`team_audit`；Skill 执行器（Skill 清单与权限校验已实现，但没有 `augur skill run`，见 [docs/skills-guide.md](docs/skills-guide.md)） |

---

## 🔒 数据与隐私

- 所有状态保存在本地数据目录（默认 `~/.augur`，`AUGUR_DATA_DIR` 可改）。没有遥测；默认单用户、无需注册（可选开启多用户模式 `AUGUR_MULTI_USER=1`）。
- 会发出的网络请求：行情与基本面（yfinance、SEC EDGAR）；可选的 LLM 调用（仅在你配置 API key 并启用相关功能时）；Dashboard 页面从 jsDelivr CDN 加载 Chart.js。
- Dashboard 默认只监听本机。需要对外暴露时先设 `AUGUR_API_TOKEN`，详见 [docs/self-hosted-guide.md](docs/self-hosted-guide.md)。

主要环境变量：

| 变量 | 作用 |
|---|---|
| `AUGUR_DATA_DIR` | 数据目录 |
| `AUGUR_EDGAR_CONTACT_EMAIL` | SEC EDGAR 要求的联系邮箱（未设置会使用占位值并告警） |
| `AUGUR_API_TOKEN` / `AUGUR_MULTI_USER` | Dashboard `/api/*` 鉴权 |
| `AUGUR_CORS_ORIGINS` | 允许的跨域来源 |
| `AUGUR_FORCE_RIC` / `AUGUR_FORCE_LEARNED` | 打开实验性动态权重 |
| `AUGUR_SKIP_MACRO_FETCH` | 跳过 VIX/SPY 宏观数据拉取（离线或 CI） |
| `AUGUR_EDGAR_GUIDANCE_EXTRACTION` | 启用基于 LLM 的 guidance 抽取（付费） |

---

## 🏗️ 开发

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,data,mcp]" "ruff>=0.16,<0.17" build

make verify     # 一条命令：全量测试 + ruff + 构建 wheel/sdist 并输出 sha256
make lint       # ruff（规则集固定为 E4/E7/E9/F）
make test-wheel # 在全新虚拟环境里安装构建产物并做冒烟检查
```

- 测试使用独立的临时 `AUGUR_DATA_DIR`，不会写入你的 `~/.augur`；在完全断网的环境下也能全部通过。
- CI（`.github/workflows/`）：`Tests` 在 Python 3.9 / 3.11 / 3.12 上跑全量测试并断言收集数；`Hermetic Smoke` 从 wheel 和 sdist 分别全新安装并跑 ruff 与 pip-audit。
- 贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 🗺️ 文档与路线图

| 文档 | 内容 |
|---|---|
| [docs/ROADMAP.md](docs/ROADMAP.md) | 唯一权威路线图：v11 RC → GA 的步骤、完成定义与待决事项 |
| [docs/RELEASE_NOTES_v11.md](docs/RELEASE_NOTES_v11.md) | v11 发布说明与迁移指南 |
| [docs/reviews/](docs/reviews/) | 项目评审记录（含每条问题的证据等级与修复） |
| [docs/schema-reference.md](docs/schema-reference.md) | EvidenceItem / Claim / StepResult / RunBundle / SkillSpec |
| [docs/api-reference-v11.md](docs/api-reference-v11.md) | Python API / REST / MCP |
| [docs/examples.md](docs/examples.md) | 实战示例 |
| [docs/self-hosted-guide.md](docs/self-hosted-guide.md) | Docker / systemd / 反向代理 / 鉴权 |
| [docs/INDEX.md](docs/INDEX.md) | 全部文档索引 |

---

## 📝 更新日志

<details open>
<summary><strong>v11.0.0-rc1 — Research Memory System (current)</strong></summary>

- **研究底座**：EvidenceItem 三类时间语义、Claim、StepResult、不可变 RunBundle、声明式 SkillSpec v1
- **研究闭环**：Thesis Journal、Filing Delta、分歧图、Guidance Tracker、研究收件箱、DCF 估值实验室
- **可信度**：缺失数据显式传播、校准状态标注、未验证的动态权重默认关闭
- **公开发布前的实测修复**：`workflow` 断点保存崩溃、证据时间戳时区错误、`export` / `research-report` / `dossier` 接上真实运行记录、`committee` 命令崩溃、SEC EDGAR 市值单位错 10⁹ 倍、估值命令编造输入、服务默认暴露到局域网、MCP 支持 `mcp` 2.x、CI 假绿修复

详见 [CHANGELOG.md](CHANGELOG.md)。
</details>

<details>
<summary><strong>v10.15.0 — 公开同步发布</strong></summary>

SEC EDGAR 真实基本面、三处可信度修复、`augur doctor` 环境诊断。
</details>

<details>
<summary><strong>v10.0.0 及更早</strong></summary>

v10：Bloomberg 风格终端 + 工作流 + MCP 工具 · v9：Hermes Agent + 委员会体系 · v8：HD-2D 设计系统
</details>

---

<div align="center">

MIT License · 维护者 [@BruceBlue](https://x.com/BruceBlue)

*仅供学习研究，不构成投资建议*

</div>
