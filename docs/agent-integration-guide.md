[English](agent-integration-guide-en.md) | 中文

# Augur Agent 整合指南

> 让18位传奇投资大师成为你的 AI Agent 伙伴，随时随地为你分析

---

## 一、产品形态全景

Augur 的18位投资人Agent可以独立存在，以多种形态嵌入你的工作流：

| 形态 | 交互方式 | 适用场景 |
|------|---------|---------|
| 🖥️ **Augur Dashboard** | Web 界面（FastAPI） | 深度分析、多Agent对比、可视化 |
| 💬 **Hermes Agent Skill** | 对话式（/skill augur） | 快速问询、日常分析 |
| 🌐 **Hermes Web UI** | 聊天界面 | 无缝集成已有 Web UI |
| 🤖 **OpenClaude (OpenClaw)** | 独立 Agent | 复杂推理任务 |
| 💻 **Claude Code / Codex** | IDE 终端 | 开发中的投资分析 |
| 📱 **Telegram / Slack** | 消息机器人 | 随时随地问询 |
| 🔧 **API 调用** | REST API | 自动化工作流 |

---

## 二、按平台接入指南

### 方式1：Augur Dashboard（自带 Web 界面）

Augur 自带一个 Bloomberg 暗色风格的 FastAPI Web Dashboard，所有18位Agent自动加载：

```bash
# 启动
cd augur && python3 -m dashboard.app

# → 访问 http://localhost:8000
# → 所有18位Agent自动加载，无需额外配置
```

Dashboard 页面一览：

| 页面 | 功能 |
|------|------|
| 🏠 首页 | 系统概览 + 快速分析入口 |
| 🤖 人格页 | 18位投资大师对比展示 |
| 📈 股票分析 | 单标的深度分析 + 实时 Agent 评分 |
| ⚡ 信号监控 | 自选股批量扫描（开发中） |
| ⚙️ 设置 | Agent 模型配置（开发中） |

```bash
# 可选参数
python3 -m dashboard.app --port 8000 --cors
```

---

### 方式2：Hermes Agent Skill

每位投资人都是一个独立 Skill（[agentskills.io](https://agentskills.io) 标准），可直接安装到 Hermes Agent。

#### 安装单个投资人 Agent

```bash
# 从本地安装
hermes skills install ./skills/buffett/SKILL.md --name buffett

# 或从 GitHub 安装
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett
```

在对话中激活：

```
/skill buffett

→ "分析 AAPL，使用巴菲特人格"
→ 返回巴菲特视角的评分、推理、信号
```

#### 安装整个 Augur 系统（所有18位大师）

```bash
# 方法一：安装主 Skill（统一调度）
hermes skills install https://github.com/BruceLanLan/augur

# 方法二：安装单独 SKILL.md（推荐用于 Hermes Agent）
hermes skills install ./SKILL.md --name augur
```

在对话中激活：

```
/skill augur

→ "分析 TSLA，对比巴菲特和马斯克"
→ 返回所有18位Agent的共识结果
```

#### 示例对话

| 用户指令 | 效果 |
|---------|------|
| `/skill augur-buffett` → "帮我用巴菲特框架分析 AAPL，PE=32，毛利率46%，ROE=55%" | 返回巴菲特视角的深度分析 |
| `/skill augur-zhang-lei` → "张磊视角评估 PDD，营收增速86%" | 张磊的长期结构性价值评估 |
| `/skill augur-dayu` → "大宇，当前 BTC 情绪怎么样？" | 大宇的币圈叙事分析 |
| `/skill augur` → "所有大师对 NVDA 怎么看？" | 18位大师共识报告 |

---

### 方式3：Hermes Web UI

在 [Hermes Web UI](https://github.com/EKKOLearnAI/hermes-web-ui) 中集成：

**方案 A：Skill 模式（推荐，零代码）**

1. 打开 Hermes Web UI
2. 在聊天窗口输入 `/skill augur` 或 `/skill buffett`
3. 直接开始对话分析

```
/skill augur
→ "分析苹果 AAPL，用巴菲特人格"
→ 结果通过 Socket.IO 流式返回
```

**方案 B：独立 Dashboard + iframe 嵌入**

1. 启动 Augur Dashboard（`python3 -m dashboard.app --port 8000 --cors`）
2. 在 Hermes Web UI 中通过 iframe 嵌入 `http://localhost:8000`

**方案 C：Hermes Agent Skill 模式**

直接通过 Skill 加载到任意 Hermes Agent 实例：
```bash
hermes skills install ./skills/buffett/SKILL.md
# 然后通过 /skill buffett 在任何平台使用
```

---

### 方式4：OpenClaude / OpenClaw

在 OpenClaude 或 OpenClaw 中注册独立 Agent。

#### OpenClaude 配置

编辑 `openclaude.yaml`：

```yaml
agents:
  buffett:
    name: "Warren Buffett"
    description: "护城河价值投资分析Agent"
    skill: "./skills/buffett/SKILL.md"
    model: "claude-sonnet-4"
  graham:
    name: "Benjamin Graham"
    description: "深度价值/安全边际分析Agent"
    skill: "./skills/graham/SKILL.md"
    model: "claude-sonnet-4"
  lynch:
    name: "Peter Lynch"
    description: "GARP成长股分析Agent"
    skill: "./skills/lynch/SKILL.md"
    model: "claude-sonnet-4"
  dayu:
    name: "大宇 (BTCdayu)"
    description: "币圈看准重仓分析Agent"
    skill: "./skills/dayu/SKILL.md"
    model: "deepseek-v4"
  duan_yongping:
    name: "段永平"
    description: "本分价值·极度集中投资分析Agent"
    skill: "./skills/duan_yongping/SKILL.md"
    model: "deepseek-v4"
  dan_bin:
    name: "但斌"
    description: "品牌护城河·时代β分析Agent"
    skill: "./skills/dan_bin/SKILL.md"
    model: "kimi-k2"
```

注册后即可直接对话：

```
> 巴菲特，当前 AAPL PE=32 毛利率46% ROE=55%，值得买入吗？
> 大宇，BTC 跌破关键支撑位，怎么看？
> 段永平，腾讯这家公司管理层本分吗？
```

#### OpenClaw 配置

OpenClaw 同样支持 Skill 文件注册，配置方式类似：

```json
{
  "agents": [
    {
      "id": "buffett",
      "name": "Warren Buffett",
      "skill": "./skills/buffett/SKILL.md",
      "model": "claude-sonnet-4"
    }
  ]
}
```

---

### 方式5：Claude Code / Codex

直接在终端使用 Claude Code 或 Codex 调用 Skill。

#### Claude Code

```bash
# 单次分析
claude -p "分析 AAPL 当前估值" --skill ./skills/buffett/SKILL.md

# 对比分析
claude -p "对比 AAPL 和 NVDA 的护城河" --skill ./skills/buffett/SKILL.md

# 中文分析
claude -p "分析茅台当前估值是否合理" --skill ./skills/duan_yongping/SKILL.md

# 币圈分析
claude -p "ETH 当前链上数据怎么看" --skill ./skills/dayu/SKILL.md
```

#### Codex

```bash
# 基本使用
codex -p "NVDA 的护城河分析" --skill ./skills/buffett/SKILL.md

# 多轮对话（需要先安装 skill）
codex --skill ./skills/buffett/SKILL.md
→ "分析 AAPL"
→ "那 MSFT 呢？"
→ "对比这两个"
```

#### 开发工作流场景

在 VSCode / Cursor 中边写代码边分析：

```bash
# 在研究某只股票时
claude -p "分析 TSLA 当前估值是否合理，PE=85 营收增速=8%"
→ 返回巴菲特、林奇、段永平三位大师的分析

# 在写投资笔记时
codex -p "用费雪框架评估 META 的成长前景，研发占比20%"
```

---

### 方式6：Telegram / Slack Bot

通过 Hermes Agent Gateway 接入消息平台。

#### Telegram

```bash
# 通过 Hermes Gateway 接入
hermes gateway setup --platform telegram

# 或使用自带 Bot
export TELEGRAM_TOKEN=your_bot_token
export AUGUR_API_URL=http://localhost:8000
python3 bots/telegram_bot.py
```

在 Telegram 中直接对话：

```
用户: /analyze AAPL pe=32 gm=46 roe=55
Bot: 18位大师分析结果...
  [共识信号: BUY | 综合评分: 7.2/10]
  🏆 Buffett: BUY (7.5/10) — 护城河优秀，毛利率满足要求
  🌐 Dalio: HOLD (6.0/10) — 宏观环境偏紧
  ...

用户: /ask buffett 你觉得现在的苹果值得持有吗？
Bot: 巴菲特视角分析结果...

用户: /consensus TSLA
Bot: 18位大师共识报告...
```

#### Slack

```bash
# 通过 Hermes Gateway 接入
hermes gateway setup --platform slack

# 或使用自带 Bot
export SLACK_TOKEN=your_slack_bot_token
export AUGUR_API_URL=http://localhost:8000
python3 bots/slack_bot.py
```

在 Slack 频道中：

```
/ask-buffett AAPL
→ 巴菲特分析结果

/consensus NVDA
→ 所有18位大师共识
```

#### 微信（开发中）

微信机器人适配器计划中，欢迎贡献（见 `bots/` 目录）。

---

### 方式7：REST API 调用

通过 Augur API 端点直接调用，适合集成到自动化工作流。

```bash
# 单标的分拆（返回所有 Agent 结果）
curl http://localhost:8000/api/analyze/AAPL

# 获取共识报告
curl http://localhost:8000/api/consensus/AAPL

# 指定 Agent
curl "http://localhost:8000/api/analyze/AAPL?agent=buffett"

# 获取投资人列表
curl http://localhost:8000/personas

# 获取人格进化时间线
curl http://localhost:8000/api/persona/buffett/evolution
```

Python 示例：

```python
import requests

response = requests.get("http://localhost:8000/api/consensus/AAPL")
data = response.json()
print(f"共识信号: {data['signal']}")
print(f"综合评分: {data['score']}")
for agent_id, result in data['agents'].items():
    print(f"  {result['name']}: {result['signal']} ({result['score']}/10)")
```

---

## 三、Skill 文件说明

每个投资人对应 `skills/{persona_id}/SKILL.md`，文件结构如下：

```
skills/
├── buffett/SKILL.md             # Warren Buffett - 护城河价值投资
├── graham/SKILL.md              # Benjamin Graham - 深度价值/安全边际
├── lynch/SKILL.md               # Peter Lynch - GARP成长
├── dalio/SKILL.md               # Ray Dalio - 宏观/全天候
├── munger/SKILL.md              # Charlie Munger - 格栅理论
├── soros/SKILL.md               # George Soros - 反身性
├── marks/SKILL.md               # Howard Marks - 周期/逆向
├── cathie_wood/SKILL.md         # Cathie Wood - 颠覆性创新
├── fisher/SKILL.md              # Philip Fisher - 成长股/闲聊法
├── arps/SKILL.md                # ARPS - Crypto/黄金宏观
├── aschenbrenner/SKILL.md       # Leopold Aschenbrenner - AI地缘政治
├── dayu/SKILL.md                # 大宇 (BTCdayu) - 信息差/情绪动量
├── thiel/SKILL.md               # Peter Thiel - 从0到1垄断
├── duan_yongping/SKILL.md       # 段永平 - 本分·极度集中
├── zhang_lei/SKILL.md           # 张磊 (高瓴) - 长期结构性价值
├── li_lu/SKILL.md               # 李录 (喜马拉雅) - 深度价值
└── dan_bin/SKILL.md             # 但斌 (东方港湾) - 品牌护城河
```

### Skill 文件结构

每个 `SKILL.md` 遵循 [agentskills.io](https://agentskills.io) 标准，包含：

| 章节 | 内容 |
|------|------|
| **身份定义** | 投资人的名字、头像、核心哲学 |
| **分析框架** | 该投资人评估公司的维度和权重 |
| **评分规则** | 针对不同因子，如何评价（加分/减分） |
| **输出格式** | 分析结果的信号输出规范（BUY/SELL/HOLD + 评分） |
| **触发条件** | 什么情况下激活该人格 |
| **示例对话** | 展示如何与该 Agent 交互 |

### 示例：巴菲特 Skill 摘要

```markdown
# Warren Buffett (沃伦·巴菲特)

## 人格定义
- 核心哲学：护城河价值投资
- 关键指标：毛利率 > 40%、ROE > 15%、负债率 < 50%
- 风格：长期持有、能力圈内、重视管理层

## 评分规则
- 护城河宽度: 高(1~3) → +2, 中(0~1) → +1, 低(<0) → -2
- 盈利能力: 毛利率 > 40% → +1, ROE > 15% → +1
- 负债水平: 总负债/总资产 < 50% → +1, > 70% → -1
- 管理层: 信任 → +1, 不信任 → -1

## 输出格式
SCORE: X.X/10
SIGNAL: BUY | SELL | HOLD
REASONING: ...
KEY_METRICS: ...
```

---

## 四、每位 Agent 的模型配置

不同投资人可使用不同的 LLM 模型。编辑 `config/agents.yaml`：

```yaml
per_agent:
  buffett:       claude-sonnet-4-6       # 英文价值分析
  graham:        claude-sonnet-4-6       # 英文深度价值
  lynch:         claude-sonnet-4-6       # GARP成长
  dalio:         claude-sonnet-4-6       # 宏观分析
  munger:        claude-sonnet-4-6       # 多元思维
  soros:         claude-sonnet-4-6       # 反身性
  marks:         claude-sonnet-4-6       # 周期投资
  cathie_wood:   claude-sonnet-4-6       # 颠覆性创新
  fisher:        claude-sonnet-4-6       # 成长股
  arps:          claude-sonnet-4-6       # Crypto/黄金
  aschenbrenner: claude-opus-4-7         # AI地缘政治（最强推理）
  dayu:          deepseek-v4             # 币圈叙事（中文社区）
  thiel:         claude-sonnet-4-6       # 垄断分析
  duan_yongping: deepseek-v4             # 中文投资分析
  zhang_lei:     deepseek-v4             # 中国结构性赛道
  li_lu:         claude-sonnet-4-6       # 全球价值投资
  dan_bin:       kimi-k2                 # 中国消费文化语境
```

支持模型：`claude-*` · `gpt-4o*` · `deepseek-v4` · `kimi-k2` · `minimax-01` · 本地 Ollama

---

## 五、自定义接入

### 5.1 创建自定义 Agent（YAML）

无需写代码，在 `personas/custom/` 下添加 YAML 文件即可自动注册：

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

参考任一 `skills/*/SKILL.md` 格式，为任意投资风格创建独立 Skill：

```bash
mkdir -p skills/my_strategy
cp skills/buffett/SKILL.md skills/my_strategy/SKILL.md
# 编辑内容，替换为你的策略
```

然后安装到任意平台：

```bash
hermes skills install ./skills/my_strategy/SKILL.md --name my-strategy
```

### 5.3 REST API 调用

自动化工作流中直接调用 API：

```bash
# 使用 curl 定时分析
0 9 * * 1-5 curl -s http://localhost:8000/api/analyze/AAPL >> ~/augur-reports.log

# 使用 Python 脚本
python3 -c "
from scanner.personas.registry import AgentRegistry, DecisionCoordinator
reg = AgentRegistry()
coord = DecisionCoordinator(reg)
results = coord.analyze_with_all(MarketContext(ticker='AAPL', ...))
print(coord.get_consensus(results, 'AAPL'))
"
```

### 5.4 独立 Agent 进程

使用 tmux 或 systemd 后台运行：

```bash
# tmux
tmux new-session -d -s augur 'cd /tmp/augur && python3 -m dashboard.app'

# systemd service
cat <<EOF | sudo tee /etc/systemd/system/augur.service
[Unit]
Description=Augur Investment Analysis Dashboard
After=network.target

[Service]
ExecStart=/usr/bin/python3 -m dashboard.app
WorkingDirectory=/tmp/augur
Restart=always
User=bruce

[Install]
WantedBy=multi-user.target
EOF
```

### 5.5 多 Agent 对比分析

通过共识引擎同时调用任意 Agent 组合进行对比：

```bash
python3 -c "
from scanner.personas.registry import AgentRegistry, DecisionCoordinator
reg = AgentRegistry()
# 只启用特定 Agent 进行对比
agents = ['buffett', 'lynch', 'dayu', 'duan_yongping']
coord = DecisionCoordinator(reg, enabled_agents=agents)
ctx = MarketContext(ticker='AAPL', ...)
results = coord.analyze_with_all(ctx)
for id, r in results.items():
    print(f'{r.agent_name:>30}: {r.signal.value.upper():>8} ({r.score:.1f}/10)')
"
```

---

## 六、架构概览

![Augur Architecture](../docs/images/architecture-baoyu.svg)

```
用户输入
  │
  ├──→ Hermes Agent Skill → SKILL.md → 调用 LLM → 返回分析结果
  ├──→ Augur Dashboard (FastAPI) → scanner/ → 18位 Agent → 共识 → 结果
  ├──→ OpenClaude/OpenClaw → 独立 Agent 进程
  ├──→ Claude Code/Codex → 终端单次分析
  ├──→ Telegram/Slack Bot → 消息平台交互
  └──→ REST API → 自动化工作流
```

---

## 七、快速参考卡片

| 平台 | 一句话安装 | 交互方式 |
|------|-----------|---------|
| Dashboard | `python3 -m dashboard.app` | Web 浏览器 |
| Hermes Agent | `hermes skills install ./SKILL.md` | 对话 `/skill augur` |
| Hermes Web UI | 聊天输入 `/skill augur` | 对话 |
| OpenClaude | 编辑 `openclaude.yaml` | 直接对话 |
| Claude Code | `claude -p "..." --skill ./SKILL.md` | 终端 |
| Codex | `codex -p "..." --skill ./SKILL.md` | 终端 |
| Telegram | `hermes gateway setup --platform telegram` | 消息 |
| Slack | `hermes gateway setup --platform slack` | 消息 |
| API | `curl localhost:8000/api/analyze/AAPL` | HTTP |

---

## 八、常见问题

**Q: 是否需要 GPU 或高性能硬件？**
A: 不需要。所有 Agent 通过 LLM API 调用，本地只需运行 FastAPI 服务。

**Q: 能否离线使用？**
A: 需要网络连接以调用 LLM API。但分析引擎本身可在本地运行，连接本地 Ollama 即可离线。

**Q: 如何添加新的投资人？**
A: 两种方式：1) 在 `personas/custom/` 下写 YAML（无需代码）；2) 在 `scanner/personas/` 下写 Python Agent（功能更强）。

**Q: 18位 Agent 可以同时工作吗？**
A: 可以。共识引擎支持并行调用所有 Agent，自动汇总结果。

**Q: 支持哪些资产类型？**
A: 美股/港股/A股/Crypto，一个系统通吃。

---

*更多问题请提交 GitHub Issue 或参考 [README.md](../README.md)*
