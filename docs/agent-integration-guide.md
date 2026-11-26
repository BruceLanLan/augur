[🇺🇸 English](en/agent-integration-guide.md) | 🇨🇳 中文

# Augur Agent 整合指南

> 让18位传奇投资大师成为你的 AI Agent 伙伴，随时随地为你分析

先说清一件事：18 位大师的**评分是确定性规则**（`src/augur/personas/`），不调用任何 LLM，离线也能跑。LLM 只出现在两处可选路径：外部 Agent（Claude Code、Hermes 等）加载 Skill 后用自己的模型对话；面板聊天在配置了 OpenAI 兼容接口时生成人格口吻的回复。

---

## 一、产品形态全景

| 形态 | 交互方式 | 适用场景 |
|------|---------|---------|
| 🖥️ **Augur Dashboard** | Web 界面（FastAPI） | 深度分析、多Agent对比、可视化 |
| 🧩 **Skill + MCP** | Hermes Studio / Claude Desktop / Claude Code / OpenClaw 等 | 对话式问询、日常分析 |
| 📱 **Telegram / Slack / 微信** | 自带消息机器人 | 随时随地问询 |
| 🔧 **REST API** | HTTP | 自动化工作流 |
| 🔗 **Agentic Workflow** | CLI / MCP / API | 多步 fetch → analyze → consensus → committee |

---

## 二、按平台接入指南

### 方式1：Augur Dashboard（自带 Web 界面）

```bash
pip install 'augur-agents[data]'
augur serve              # 默认 http://127.0.0.1:8000
augur serve --port 8080  # 自定义端口
augur serve --open       # 启动后自动打开浏览器
```

所有 18 位大师自动加载，无需额外配置。对外暴露请用 `--host 0.0.0.0`，并先设置 `AUGUR_API_TOKEN`。

主要页面：

| 页面 | 功能 |
|------|------|
| 🏠 `/` | 系统概览 + 快速分析入口 |
| 🤖 `/personas` | 18位投资大师对比展示 |
| 📈 `/stocks` | 单标的深度分析 + 实时 Agent 评分 |
| ⚡ `/signals`、`/scanner` | 信号监控与批量扫描 |
| 🧪 `/backtest` | 历史回测（命中率 / IC） |
| ⚙️ `/settings` | 设置 |

---

### 方式2：Skill + MCP（Hermes Studio、Claude Desktop、OpenClaw 等）

每位大师在仓库里是一个 Skill 目录：`src/skills/augur-<id>/`，内含：

- `SKILL.md` — YAML frontmatter + 人格 system prompt
- `manifest.json` — 通用 JSON 清单（OpenClaw、Hermes Studio、Claude Desktop 等读取）

另有 `src/skills/augur-committee/`（投委会协调者）和 `src/skills/augur-terminal/`。Skill 通过 Augur MCP 服务器拿数据和评分，所以先确保 `augur-mcp` 可用：

```bash
pip install 'augur-agents[data,mcp]'
augur-mcp            # stdio 模式的 MCP 服务器（等价于 augur mcp-server）
```

各平台的接法以 [src/skills/README.md](../src/skills/README.md) 为准，要点如下。

#### Hermes Studio

```yaml
# hermes/config.yaml
mcp_servers:
  augur:
    command: augur-mcp

skills_dir: ./src/skills
```

然后在对话中激活：`/skill augur-buffett`、`/skill augur-committee` 等。

#### Claude Desktop

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

把需要的 `SKILL.md` 内容作为 system prompt 使用。

#### OpenClaw

OpenClaw 读取 Skill 目录下的 `manifest.json`，安装命令见 [src/skills/README.md](../src/skills/README.md) 的 OpenClaw 一节（指向 `src/skills/augur-<id>` 目录）。

#### 示例对话

| 用户指令 | 效果 |
|---------|------|
| `/skill augur-buffett` → "帮我用巴菲特框架分析 AAPL" | 巴菲特视角的分析（数据与评分来自 MCP 工具） |
| `/skill augur-zhang-lei` → "张磊视角评估 PDD" | 张磊的长期结构性价值评估 |
| `/skill augur-dayu` → "大宇，当前 BTC 情绪怎么样？" | 大宇的币圈叙事分析 |
| `/skill augur-committee` → "所有大师对 NVDA 怎么看？" | 投委会共识报告 |

---

### 方式3：Claude Code / Codex

Claude Code 没有 `--skill` 参数；接入方式是注册 MCP 服务器，再把 Skill 放进 Claude Code 的 skills 目录。

```bash
# 注册 Augur MCP 服务器（stdio）
claude mcp add augur -- augur-mcp

# 可选：把某位大师作为项目级 Skill（Claude Code 读取 .claude/skills/<name>/SKILL.md）
mkdir -p .claude/skills/augur-buffett
cp src/skills/augur-buffett/SKILL.md .claude/skills/augur-buffett/SKILL.md

# 非交互单次调用
claude -p "用 augur 的 MCP 工具分析 AAPL 的共识"
```

Codex 等其他支持 MCP 的终端 Agent：把 `augur-mcp` 注册为 stdio MCP 服务器（具体命令以该工具文档为准），再把 `SKILL.md` 内容作为指令使用。

#### v14 的 MCP 变化

- **ETF**：`augur_analyze`、`augur_consensus`、`augur_debate`、`augur_committee` 接受 `asset_type`（`equity` / `etf` / `fund`，留空自动识别）。基金上 18 位大师里 Dalio、Marks、Soros、ARPS 用技术面和行情给出读数，其余返回"不适用"；适用的至少 3 位时给出"基金共识"（等权、不给仓位、不写学习记录）；技术指标缺失导致适用不足 3 位时共识被**扣下（withheld）**，不给信号和仓位。`augur_fetch` 对基金输出 ETF 概况与体检清单。
- **`augur_configure` 已弃用**：Augur 的评分不调用模型，这个工具写的配置从来没有被读取。v14 起调用它只返回一条弃用说明，不写任何文件。模型由宿主 Agent（例如 Claude Code）自己决定。

---

### 方式4：Telegram / Slack / 微信 Bot

#### Telegram

```bash
pip install 'augur-agents[telegram,data]'
export TELEGRAM_TOKEN=your_bot_token
augur telegram
```

可用命令：`/analyze`、`/consensus`、`/ask`、`/personas`、`/help`。

```
用户: /analyze AAPL pe=32 gm=46 roe=55
用户: /ask buffett 你觉得现在的苹果值得持有吗？
用户: /consensus TSLA
```

#### Slack

```bash
pip install 'augur-agents[slack,data]'
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_APP_TOKEN=xapp-...
augur slack
```

Slash 命令：`/augur-analyze TICKER [pe=X roe=X ...]`（或 `/augur`）、`/augur-ask`、`/augur-personas`、`/augur-help`。

#### 微信

```bash
pip install 'augur-agents[wechat]'
export GEWECHAT_TOKEN='...' GEWECHAT_BASE_URL='http://127.0.0.1:2531/v2/api'
augur wechat --mode personal --port 8066
```

支持个人微信(GeWeChat)、企业微信、Webhook三种模式。详见 [README](../README.md)。

---

### 方式5：REST API 调用

Dashboard（`augur serve`，端口 8000）上的常用端点：

```bash
# 单标的分析：返回 consensus（共识）+ agents（每位大师）+ market_data
curl http://localhost:8000/api/analyze/AAPL

# 手动给指标（不联网取数）
curl "http://localhost:8000/api/analyze/AAPL?price=210&pe=32&gross_margins=0.46&roe=0.55"

# 投资人列表 / 单个投资人
curl http://localhost:8000/api/personas
curl http://localhost:8000/api/persona/buffett

# 健康检查（含版本号）
curl http://localhost:8000/api/health
```

Python 示例：

```python
import requests

data = requests.get("http://localhost:8000/api/analyze/AAPL").json()
print(f"共识信号: {data['consensus']['signal']}")
print(f"综合评分: {data['consensus']['score']:.1f}")
for a in data["agents"]:
    print(f"  {a['agent_name']}: {a['signal']} ({a['score']:.1f}/10)")
```

---

### 方式6：Agentic Workflow 多步流水线

运行可配置的多步分析流水线：**fetch → analyze → consensus → committee → debate → sentiment**。

#### CLI

```bash
# 默认：fetch, analyze, consensus
augur workflow AAPL

# 完整投委会流水线
augur workflow AAPL --steps fetch,analyze,consensus,committee

# 指定 Agent + 投委会问题
augur workflow NVDA --agents buffett,munger,dalio --steps fetch,analyze,committee -q "护城河是在扩大还是缩小？"

# JSON 输出（便于脚本集成）
augur workflow TSLA --steps fetch,consensus,sentiment --json
```

有效步骤：`fetch`、`analyze`、`consensus`、`committee`、`debate`、`sentiment`。

#### MCP 工具

使用 `augur-mcp`（或 `augur mcp-server`）时，调用 `augur_workflow` 工具：

```
augur_workflow(ticker="AAPL", steps="fetch,analyze,consensus,committee")
```

可选参数：`agents`（逗号分隔 ID）、`question`（投委会问题）。

#### REST API

独立的 REST API 服务器（`augur api`，默认端口 8900）提供 `/api/workflow`：

```bash
augur api   # http://127.0.0.1:8900

curl -X POST http://localhost:8900/api/workflow \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","steps":"fetch,analyze,consensus,committee"}'
```

Python 示例：

```python
import requests

resp = requests.post(
    "http://localhost:8900/api/workflow",
    json={
        "ticker": "AAPL",
        "steps": "fetch,analyze,consensus,committee",
        "question": "当前估值是否值得加仓？",
    },
)
data = resp.json()
print(data["step_status"])
print(data["results"]["consensus"]["signal"])
```

---

## 三、Skill 文件说明

```
src/skills/
├── augur-buffett/{SKILL.md,manifest.json}        # Warren Buffett - 护城河价值投资
├── augur-graham/                                 # Benjamin Graham - 深度价值/安全边际
├── augur-lynch/                                  # Peter Lynch - GARP成长
├── augur-dalio/                                  # Ray Dalio - 宏观/全天候
├── augur-munger/                                 # Charlie Munger - 格栅理论
├── augur-soros/                                  # George Soros - 反身性
├── augur-marks/                                  # Howard Marks - 周期/逆向
├── augur-cathie-wood/                            # Cathie Wood - 颠覆性创新
├── augur-fisher/                                 # Philip Fisher - 成长股/闲聊法
├── augur-arps/                                   # ARPS - Crypto/黄金宏观
├── augur-aschenbrenner/                          # Leopold Aschenbrenner - AI地缘政治
├── augur-dayu/                                   # 大宇 (BTCdayu) - 信息差/情绪动量
├── augur-thiel/                                  # Peter Thiel - 从0到1垄断
├── augur-duan-yongping/                          # 段永平 - 本分·极度集中
├── augur-zhang-lei/                              # 张磊 (高瓴) - 长期结构性价值
├── augur-li-lu/                                  # 李录 (喜马拉雅) - 深度价值
├── augur-dan-bin/                                # 但斌 (东方港湾) - 品牌护城河
├── augur-serenity/                               # Serenity - AI/半导体供应链瓶颈
├── augur-committee/                              # 投委会协调者
└── augur-terminal/                               # 终端工作区
```

目录名用连字符（`augur-duan-yongping`），而 CLI / API 里的 persona ID 用下划线（`duan_yongping`）。

### Skill 文件结构

- **frontmatter**：`name`、`description`、`version`、建议模型、`metadata.augur.persona`（对应的 persona ID）、`mcp_required: augur-mcp`。
- **正文**：该大师的 system prompt——口吻、核心信条、如何调用 Augur MCP 工具取数和评分。
- 真正的评分规则在 `src/augur/personas/<id>.py`（或 `personas/custom/*.yaml`），Skill 本身不含打分逻辑。

---

## 四、每位 Agent 的模型配置

`config/agents.yaml` 记录每位大师建议使用的 LLM（`defaults` + `per_agent`），面板设置页会读取它。注意：这个文件**不影响评分**——评分是确定性规则；它只对使用 Skill 的外部 Agent 和可选的聊天 LLM 路径有参考意义。

---

## 五、自定义接入

### 5.1 创建自定义 Agent（YAML）

无需写代码，在 `personas/custom/` 下添加 YAML 文件即可自动注册（格式参考 `personas/custom/thiel.yaml`）：

```yaml
agent_id: my_quant
name: "我的量化策略"
description: "基于技术指标的量化策略Agent"
scoring_weights:
  momentum: 0.50
  value: 0.50
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 60 and rsi < 75", add: 2}
      - {if: "macd > macd_signal", add: 1}
  value:
    base: 5
    rules:
      - {if: "pe < 15", add: 2}
      - {if: "pb < 1.5", add: 1}
```

### 5.2 创建自定义 Skill

以任一 Skill 目录为模板：

```bash
cp -r src/skills/augur-buffett src/skills/augur-my-strategy
# 编辑 SKILL.md 与 manifest.json：改 name、description、metadata.augur.persona 和正文
```

然后按方式2中对应平台的方式加载。

### 5.3 在 Python 里直接调用

```bash
# 定时分析（cron）
0 9 * * 1-5 curl -s http://localhost:8000/api/analyze/AAPL >> ~/augur-reports.log
```

```python
from augur.personas.base import MarketContext
from augur.registry import AgentRegistry, DecisionCoordinator

coord = DecisionCoordinator(AgentRegistry())
ctx = MarketContext(ticker="AAPL", price=210, pe=32, gross_margins=0.46, roe=0.55)
results = coord.analyze_with_all(ctx)
consensus = coord.get_consensus(results, ticker="AAPL", context=ctx)
print(consensus.signal.value, round(consensus.score, 1))
```

### 5.4 独立 Agent 进程

使用 tmux 或 systemd 后台运行：

```bash
# tmux
tmux new-session -d -s augur 'augur serve --port 8000'

# systemd service（ExecStart 换成你环境里 augur 的绝对路径，如 `which augur` 的输出）
cat <<EOF | sudo tee /etc/systemd/system/augur.service
[Unit]
Description=Augur Investment Analysis Dashboard
After=network.target

[Service]
ExecStart=/usr/local/bin/augur serve --port 8000
Restart=always
User=augur

[Install]
WantedBy=multi-user.target
EOF
```

### 5.5 多 Agent 对比分析

只启用部分大师：

```python
from augur.personas.base import MarketContext
from augur.registry import AgentRegistry, DecisionCoordinator

coord = DecisionCoordinator(AgentRegistry())
ctx = MarketContext(ticker="AAPL", price=210, pe=32, gross_margins=0.46, roe=0.55)
results = coord.analyze_with_all(ctx, enabled_personas=["buffett", "lynch", "dayu", "duan_yongping"])
for agent_id, r in results.items():
    print(f"{r.agent_name:>30}: {r.signal.value.upper():>8} ({r.score:.1f}/10)")
```

---

## 六、架构概览

![Augur Architecture](images/architecture-baoyu.svg)

```
用户输入
  │
  ├──→ Skill（Hermes Studio / Claude Desktop / Claude Code / OpenClaw）→ augur-mcp → 18位 Agent → 共识
  ├──→ Augur Dashboard（augur serve）→ src/augur/ → 18位 Agent → 共识 → 结果
  ├──→ Telegram / Slack / 微信 Bot → 消息平台交互
  └──→ REST API（augur serve / augur api）→ 自动化工作流
```

---

## 七、快速参考卡片

| 平台 | 一句话启动 | 交互方式 |
|------|-----------|---------|
| Dashboard | `augur serve` | Web 浏览器 |
| MCP 服务器 | `augur-mcp` | 任意 MCP 客户端 |
| Hermes Studio | `mcp_servers.augur.command: augur-mcp` + `skills_dir: ./src/skills` | 对话 `/skill augur-buffett` |
| Claude Code | `claude mcp add augur -- augur-mcp` | 终端 |
| Telegram | `augur telegram` | 消息 |
| Slack | `augur slack` | 消息 |
| API | `curl localhost:8000/api/analyze/AAPL` | HTTP |

---

## 八、常见问题

**Q: 是否需要 GPU 或高性能硬件？**
A: 不需要。评分是本地规则计算，只需运行 Python。

**Q: 能否离线使用？**
A: 评分引擎可以完全离线（手动传入指标，或使用缓存数据）；实时行情需要联网取数。LLM 只在可选的聊天路径和外部 Agent 里用到。

**Q: 如何添加新的投资人？**
A: 两种方式：1) 在 `personas/custom/` 下写 YAML（无需代码）；2) 在 `src/augur/personas/` 下写 Python Agent（功能更强）。

**Q: 18位 Agent 可以同时工作吗？**
A: 可以。`analyze_with_all` 并行调用所有 Agent，共识引擎自动汇总结果。

**Q: 支持哪些资产类型？**
A: 美股/港股/A股/Crypto，一个系统通吃。

---

*更多问题请提交 GitHub Issue 或参考 [README.md](../README.md)*
