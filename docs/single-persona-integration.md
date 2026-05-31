# 单个投资人 Agent 接入指南 / Single Persona Integration Guide

> **中文** | [English below](#english-version)

> 你完全可以**只挑选自己喜欢的某一位投资大师**（比如巴菲特、段永平、大宇/dayu、查理芒格等），把他单独接入到你自己的 Hermes Agent 或 Open Claw，而**不必引入全部 18 位**。本文给出多种真实可用的接入方式，每种都有可复制的命令与配置示例。

---

## 零、直接 Python API 调用（最简单）

如果你只是想在自己的 Python 项目中调用某位投资人的分析逻辑，无需启动任何服务：

```python
from augur.registry import AgentRegistry
from augur.personas.base import MarketContext

# 初始化注册表，获取单个投资人
registry = AgentRegistry()
buffett = registry.get("buffett")  # 或 "dayu", "duan_yongping" 等

# 构造市场数据上下文
ctx = MarketContext(
    ticker="AAPL",
    price=210.0,
    pe=32.0,
    pb=48.0,
    gross_margins=0.46,
    roe=0.55,
    revenue_growth=0.08,
    market_cap=3200,  # billions
    sector="Technology",
    industry="Consumer Electronics",
)

# 执行单 Agent 分析
result = buffett.analyze(ctx)

print(f"Signal: {result.signal.value}")    # bullish / neutral / bearish
print(f"Score:  {result.score}/10")
print(f"Confidence: {result.confidence}")
print(f"Reasoning: {result.reasoning}")
print(f"Key Findings: {result.key_findings}")
print(f"Risks: {result.risks}")
```

**自动获取实时数据**（需安装 `pip install -e '.[data]'`）：

```python
from augur.data import fetch_market_context
from augur.registry import AgentRegistry

registry = AgentRegistry()
dayu = registry.get("dayu")

# 自动从 yfinance 获取实时数据
ctx = fetch_market_context("BTC-USD")
result = dayu.analyze(ctx)
print(f"大宇观点: {result.signal.value} ({result.score}/10)")
```

---

## 零-B、REST API 单人格调用

启动 Augur Dashboard 后，可通过 HTTP 接口调用单个投资人：

```bash
# 启动服务
python -m dashboard.app --port 8000
```

**获取单个投资人信息：**
```bash
GET /api/persona/buffett
```

**使用全部 18 位分析（包含单人格结果）：**
```bash
GET /api/analyze/AAPL
# 返回 JSON 中 agents 数组包含每位投资人的独立评分
```

**提取单人格结果示例（Python）：**
```python
import requests

resp = requests.get("http://localhost:8000/api/analyze/AAPL")
data = resp.json()

# 从 agents 数组中筛选出巴菲特的结果
buffett_result = next(
    (a for a in data["agents"] if a["agent_id"] == "buffett"), None
)
if buffett_result:
    print(f"Buffett: {buffett_result['signal']} ({buffett_result['score']}/10)")
```

---

## 一、当前支持的投资人列表（persona id）

下表中的 `persona id` 就是接入时要填写的标识，与 `skills/<persona id>/` 目录名、`augur analyze --persona <id>`、`augur inject-soul --persona <id>` 完全一致。

| 中文名 | 英文 / 拼音 | persona id | 投资风格（一句话） |
|--------|------------|------------|--------------------|
| 巴菲特 | Warren Buffett | `buffett` | 护城河价值投资，长期持有优秀企业 |
| 格雷厄姆 | Benjamin Graham | `graham` | 深度价值 / 安全边际（PE<15、PB<1.5）|
| 彼得·林奇 | Peter Lynch | `lynch` | GARP 成长（PEG<1.5、日常可理解的生意）|
| 达利欧 | Ray Dalio | `dalio` | 全天候宏观 + 债务周期 |
| 芒格 | Charlie Munger | `munger` | 格栅多元思维 + 逆向 |
| 索罗斯 | George Soros | `soros` | 反身性 + 趋势自我强化 |
| 霍华德·马克斯 | Howard Marks | `marks` | 周期钟摆情绪 + 二阶思考 |
| 凯西·伍德 | Cathie Wood | `cathie_wood` | 颠覆性创新（Wright 定律 + TAM 扩张）|
| 费雪 | Philip Fisher | `fisher` | 成长股 + 闲聊法（Scuttlebutt）|
| ARPS | ARPS | `arps` | 实际利率驱动的 Crypto / 黄金宏观 |
| 阿申布伦纳 | Leopold Aschenbrenner | `aschenbrenner` | AGI 基础设施 + 算力稀缺 |
| 大宇 | BTCdayu | `dayu` | 信息差 + 情绪动量，Crypto 叙事驱动 |
| 蒂尔 | Peter Thiel | `thiel` | 从 0 到 1 垄断 + 逆向思考 |
| 段永平 | Duan Yongping | `duan_yongping` | 本分 + 极度集中 |
| 张磊 | Zhang Lei（高瓴）| `zhang_lei` | 长期结构性价值 |
| 李录 | Li Lu（喜马拉雅）| `li_lu` | 深度价值 + 安全边际 |
| 但斌 | Dan Bin（东方港湾）| `dan_bin` | 品牌护城河 + 时代 β |
| Serenity | Serenity（@aleabitoreddit）| `serenity` | AI / 半导体供应链瓶颈 |

> 提示：**段永平**（`duan_yongping`）和**大宇**（`dayu`）是两位不同的投资人。前者是「本分价值」中国实业投资人，后者是中国加密社区 KOL。本文示例同时演示 `buffett` 与 `dayu`，你也可以把命令里的 id 换成上表任意一位。
>
> 随时可以用下面这条命令在本机确认当前可用的全部 persona id：
>
> ```bash
> augur list-personas
> ```

---

## 二、三种接入方式总览

| 方式 | 适合谁 | 接入产物 | 是否需要常驻进程 |
|------|--------|----------|------------------|
| **方式 A：Skills 机制** | Open Claw / Claude / Hermes 用户，想要「对话式」单人格 | 复制 `skills/<persona>/SKILL.md` | 否（Skill 文件即可）|
| **方式 B：MCP Server** | Hermes / Claude Desktop 用户，想让 agent 自动调用工具拿真实数据 | 注册 `augur mcp-server`，调用时传 `persona` 参数 | 是（MCP server 进程）|
| **方式 C：inject-soul** | 任意平台，想把投资人「灵魂」直接写进自己 agent 的系统提示词 | 生成 `soul.md` / `*.json` 注入 | 否（一次性生成文件）|

---

## 方式 A：通过 Skills 机制接入单个 persona

每位投资人都是一个**独立的 Skill**，对应目录 `skills/<persona id>/SKILL.md`（遵循 [agentskills.io](https://agentskills.io) 标准）。接入单人格，本质上就是**只拿走这一个目录**。

每个 `SKILL.md` 顶部的 frontmatter 里已经写好了它的 Skill 名与触发词，例如：

- `skills/buffett/SKILL.md` → `name: augur-buffett`，触发词 `/skill augur-buffett`、`@buffett`、`@巴菲特`
- `skills/dayu/SKILL.md` → `name: augur-dayu`，触发词 `/skill augur-dayu`、`@dayu`、`@大宇`

### A-1：Open Claw 接入单个 persona

Open Claw 通过 JSON 配置注册 Skill 文件，只列出你想要的那一位即可：

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

只想接入大宇时，把这一段换成：

```json
{
  "agents": [
    {
      "id": "dayu",
      "name": "大宇 (BTCdayu)",
      "skill": "./skills/dayu/SKILL.md",
      "model": "deepseek-v4"
    }
  ]
}
```

注册后即可直接对话（无需引入其他 17 位）：

```
> 巴菲特，当前 AAPL PE=32 毛利率46% ROE=55%，值得买入吗？
> 大宇，BTC 跌破关键支撑，现在该减仓还是拿着？
```

### A-2：Hermes 接入单个 persona Skill

**做法一：只暴露单个 skill 目录给 Hermes**

把单个目录复制到一个独立目录，然后在 `~/.hermes/config.yaml` 中只把这个目录加入 `skills.external_dirs`：

```bash
# 只取巴菲特一位
mkdir -p ~/my-augur-skills
cp -r ./skills/buffett ~/my-augur-skills/buffett

# 想要大宇就改成：
# cp -r ./skills/dayu ~/my-augur-skills/dayu
```

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - /home/you/my-augur-skills    # 只包含 buffett（或 dayu）一个目录
```

**做法二：用 hermes 命令单独安装某一个 SKILL.md**

```bash
# 从本地安装单个投资人
hermes skills install ./skills/buffett/SKILL.md --name buffett

# 大宇：
hermes skills install ./skills/dayu/SKILL.md --name dayu

# 也支持从 GitHub 子目录安装单个
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett
```

在对话中激活：

```
/skill augur-buffett
→ "帮我用巴菲特框架分析 AAPL，PE=32，毛利率46%，ROE=55%"

/skill augur-dayu
→ "大宇，当前 BTC 情绪怎么样？该不该追？"
```

> 说明：`/skill` 后面跟的是 `SKILL.md` frontmatter 里的 `name`（`augur-buffett` / `augur-dayu`）。若你用 `--name buffett` 覆盖了名字，则用 `/skill buffett`。

---

## 方式 B：通过 MCP Server 接入（单 persona 调用）

Augur 自带的 MCP Server（`augur mcp-server`）会暴露 7 个工具。它**不是为每位投资人单独建一个 server**，而是用统一的 `augur_analyze` 工具，通过 `persona` 参数指定**只用某一位**投资人分析。也就是说：你照常注册一次 MCP Server，但在调用时锁定单个 persona，就实现了"只用巴菲特/只用大宇"。

### B-1：注册 MCP Server（一次性）

先确认能启动：

```bash
augur mcp-server      # 无报错即正常，Ctrl+C 退出
```

**Hermes**（`~/.hermes/config.yaml`）：

```yaml
mcp_servers:
  augur:
    command: /绝对路径/augur/.venv/bin/augur
    args: [mcp-server]
    description: "Augur 投资分析（支持按单个投资人分析）"
```

**Claude Desktop**（`claude_desktop_config.json`）：

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

### B-2：调用时锁定单个 persona

`augur_analyze` 工具签名里有一个 `persona` 参数。只要带上它，就只用那一位分析（不传则是 18 位一起）：

- 巴菲特：调用 `augur_analyze`，参数 `ticker="AAPL"`, `persona="buffett"`
- 大宇：调用 `augur_analyze`，参数 `ticker="BTC-USD"`, `persona="dayu"`

在 Hermes / Claude 对话里，直接用自然语言引导它带上 persona：

```
用巴菲特（persona=buffett）分析 AAPL，PE=32，毛利率46%，ROE=55%
用大宇（persona=dayu）只从他的视角看一下 BTC 现在的情绪和仓位建议
```

> 小技巧：`skills/buffett/SKILL.md` 的 frontmatter 已经把 MCP 默认参数写好了——
> ```yaml
> mcp:
>   server: augur-agents
>   tool: augur_analyze
>   default_args:
>     persona: buffett
> ```
> 所以如果你**同时**用方式 A 装了该 Skill，再叠加 MCP Server，Skill 会自动以 `persona=buffett` 去调 `augur_analyze`，相当于"单人格 + 真实数据"二合一。

### B-3：命令行先行验证（不依赖任何平台）

接入平台前，可以先在本机用 CLI 跑通单 persona，确认结果符合预期：

```bash
# 巴菲特单人格
augur analyze AAPL --persona buffett --pe 32 --roe 0.55 --gross-margins 0.46

# 大宇单人格（自动抓取实时数据）
augur analyze BTC-USD --persona dayu
```

---

## 方式 C：通过 inject-soul 把单个投资人的"灵魂"注入你的 agent

如果你不想跑任何 Augur 服务，只想**把某位投资人的完整人格（系统提示词 + 人格文档 + 评分规则）直接塞进你自己 agent 的提示词**里，就用 `augur inject-soul`。它会读取该 persona 的源码与 `personas/*.md` 文档，生成一个可直接使用的 soul 文件。

命令格式（来自 `cli.py` 真实定义）：

```bash
augur inject-soul --profile <你的profile名> --persona <persona id> \
  --format <hermes|claude|raw> --output-dir <输出目录>
```

- `--format hermes` → 在 `<输出目录>/<profile>/soul.md` 生成（适合 Hermes Profile）
- `--format claude` → 生成 `<输出目录>/<profile>-claude.json`（含 `system_prompt` 字段，适合 Open Claw / Claude 类系统直接读取）
- `--format raw` → 生成 `<输出目录>/<profile>-soul.md`（纯 markdown，适合贴进任意 agent 的 system prompt）

### C-1：巴菲特

```bash
# 生成 Hermes Profile（写入 ~/.hermes/profiles/buffett-advisor/soul.md）
augur inject-soul --profile buffett-advisor --persona buffett \
  --format hermes --output-dir ~/.hermes/profiles/

# 生成给 Open Claw / Claude 用的 JSON（含 system_prompt）
augur inject-soul --profile buffett-advisor --persona buffett \
  --format claude --output-dir ./my-agent/
# → 产物：./my-agent/buffett-advisor-claude.json
```

在 Hermes Web UI 中，在侧边栏切换到 `buffett-advisor` 这个 Profile，之后该 Profile 的所有对话都会以巴菲特的视角回答。

### C-2：大宇（dayu）

```bash
# Hermes Profile
augur inject-soul --profile dayu-trader --persona dayu \
  --format hermes --output-dir ~/.hermes/profiles/

# raw 纯文本（直接复制到你 agent 的 system prompt）
augur inject-soul --profile dayu-trader --persona dayu \
  --format raw --output-dir ./
# → 产物：./dayu-trader-soul.md，打开后整段贴进 Open Claw 的系统提示词即可
```

> 想接入段永平而不是大宇？把 `--persona dayu` 换成 `--persona duan_yongping` 即可，其余不变。

---

## 三、三种方式怎么选？

- **只想对话、零服务** → 方式 A（Skills）或方式 C（inject-soul raw）。
- **希望 agent 自动拉实时行情再分析** → 方式 B（MCP Server + `persona` 参数），因为 `augur_analyze` 在不传指标时会自动用 yfinance 抓数据。
- **想把人格"焊死"进自己 agent 的底层提示词** → 方式 C（inject-soul）。

三者也可叠加：典型组合是 **A + B**（Skill 负责对话风格，MCP 负责真实数据），见方式 B-2 的说明。

---

## 四、常见问题

**Q1：我能不能同时接入两三位，而不是只接一位？**
能。三种方式都支持：

- 方式 A：在 Open Claw 的 `agents` 数组里多列几位；或多复制几个 `skills/<id>` 目录。
- 方式 B：同一个 MCP Server 即可，调用 `augur_analyze` 时分别传不同 `persona`；若想直接看"这几位的加权共识"，可改用 `augur_consensus`（它默认汇总全部 18 位）。
- 方式 C：对每位分别执行一次 `augur inject-soul`（用不同的 `--profile` 名）。

**Q2：接入单个投资人需要 API key 吗？**
Augur 引擎本身（评分逻辑、共识、inject-soul、CLI）**不需要任何 API key**。需要 key 的是两类外部能力：

- 让投资人"开口说话"的 LLM——由你的 Hermes / Open Claw / Claude 平台自己的模型配置提供，Augur 只产出提示词与结构化评分。
- 实时行情数据用的是 `yfinance`（`pip install -e ".[data]"`），同样不需要 key。

**Q3：怎么给单个投资人指定使用的模型？**
两种办法：

- Skill / Open Claw 配置里直接写 `model` 字段（见方式 A 的 JSON）。
- 用 Augur 的配置：`augur configure` 对应的 MCP 工具 `augur_configure(persona_id, model)`，或编辑 `config/agents.yaml` 的 `per_agent` 段，例如：
  ```yaml
  per_agent:
    buffett: claude-sonnet-4-6
    dayu:    deepseek-v4
  ```

**Q4：以后投资人的逻辑更新了，我怎么同步？**
- 方式 A / C 是"快照"式：更新代码后（`git pull` + `pip install -e .`），重新执行一次 `hermes skills install ...` 或重新跑 `augur inject-soul ...` 覆盖旧文件即可。
- 方式 B 是"实时"式：MCP Server 每次调用都读取最新引擎逻辑，更新代码并重启 `augur mcp-server` 后自动生效，无需重新生成文件。

**Q5：persona id 填错了会怎样？**
CLI / MCP 会直接报 `Persona '<id>' not found` 并列出全部可用 id。用 `augur list-personas` 查正确拼写（注意 `cathie_wood`、`duan_yongping`、`zhang_lei`、`li_lu`、`dan_bin` 用下划线）。

**Q6：单个投资人也能拿到实时数据吗？**
能。走方式 B 时，`augur_analyze` 不传财务指标会自动用 yfinance 抓取；走 CLI 验证（方式 B-3）时，`augur analyze <ticker> --persona <id>` 不带指标同样会自动抓取。

---

*相关文档：[agent-integration-guide.md](agent-integration-guide.md)（整体接入引导）、[hermes-setup-guide.md](hermes-setup-guide.md)（Hermes 完整配置）。仅供学习研究，不构成投资建议。*

---

## 五、MCP 配置示例（Claude Desktop / Hermes）

### Claude Desktop 配置

在 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）或 `%APPDATA%\Claude\claude_desktop_config.json`（Windows）中添加：

```json
{
  "mcpServers": {
    "augur": {
      "command": "python",
      "args": ["-m", "augur.mcp_server"],
      "env": {
        "AUGUR_DEFAULT_PERSONA": "buffett"
      }
    }
  }
}
```

如果使用虚拟环境：

```json
{
  "mcpServers": {
    "augur": {
      "command": "/path/to/augur/.venv/bin/python",
      "args": ["-m", "augur.mcp_server"],
      "env": {
        "AUGUR_DEFAULT_PERSONA": "buffett"
      }
    }
  }
}
```

### Hermes MCP 配置

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  augur:
    command: /path/to/augur/.venv/bin/augur
    args: [mcp-server]
    description: "Augur single-persona analysis (default: buffett)"
    env:
      AUGUR_DEFAULT_PERSONA: buffett
```

---

## 六、自定义 Wrapper 示例（Open Claw / 其他框架）

如果你使用 Open Claw 或其他 Agent 框架，可以创建一个简单的 wrapper：

```python
"""
augur_wrapper.py - 将 Augur 单个投资人封装为工具函数
适用于 Open Claw、LangChain、AutoGen 等框架
"""
from augur.registry import AgentRegistry
from augur.personas.base import MarketContext

class AugurPersonaTool:
    """封装单个 Augur 投资人为可调用的工具。"""

    def __init__(self, persona_id: str = "buffett"):
        self.registry = AgentRegistry()
        self.agent = self.registry.get(persona_id)
        if not self.agent:
            raise ValueError(f"Persona '{persona_id}' not found")
        self.persona_id = persona_id

    def analyze(self, ticker: str, **kwargs) -> dict:
        """分析标的，返回结构化结果。"""
        # 尝试自动获取数据
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
        except (ImportError, Exception):
            ctx = MarketContext(ticker=ticker.upper(), **kwargs)

        result = self.agent.analyze(ctx)
        return {
            "persona": self.persona_id,
            "ticker": ticker.upper(),
            "signal": result.signal.value,
            "score": round(result.score, 1),
            "confidence": round(result.confidence, 2),
            "reasoning": result.reasoning,
            "key_findings": result.key_findings,
            "risks": result.risks,
        }

    @property
    def description(self) -> str:
        return f"Augur {self.agent.name} - {self.agent.identity[:100]}"


# === 用法示例 ===
if __name__ == "__main__":
    # 创建巴菲特工具
    buffett_tool = AugurPersonaTool("buffett")
    result = buffett_tool.analyze("AAPL")
    print(result)

    # 创建大宇工具
    dayu_tool = AugurPersonaTool("dayu")
    result = dayu_tool.analyze("BTC-USD")
    print(result)
```

### Open Claw 注册示例

```python
from augur_wrapper import AugurPersonaTool

# 注册为 Open Claw 工具
tools = [
    {
        "name": "buffett_analyze",
        "description": "使用巴菲特价值投资框架分析股票",
        "function": AugurPersonaTool("buffett").analyze,
        "parameters": {
            "ticker": {"type": "string", "description": "Stock ticker symbol"}
        }
    }
]
```

### LangChain Tool 示例

```python
from langchain.tools import tool
from augur_wrapper import AugurPersonaTool

buffett = AugurPersonaTool("buffett")

@tool
def buffett_analyze(ticker: str) -> str:
    """使用巴菲特价值投资框架分析指定股票。"""
    result = buffett.analyze(ticker)
    return f"Signal: {result['signal']}, Score: {result['score']}/10\n{result['reasoning']}"
```

---

<a id="english-version"></a>

# English Version: Single Persona Integration Guide

> You can pick **just one investment master** (e.g., Buffett, Dayu, Duan Yongping, Munger) and integrate only that persona into your Hermes Agent, Open Claw, or any custom system -- without pulling in all 18 masters. This guide provides multiple integration methods with copy-paste examples.

## Direct Python API (Simplest)

```python
from augur.registry import AgentRegistry
from augur.personas.base import MarketContext

registry = AgentRegistry()
buffett = registry.get("buffett")  # or "dayu", "duan_yongping", etc.

ctx = MarketContext(
    ticker="AAPL",
    price=210.0,
    pe=32.0,
    gross_margins=0.46,
    roe=0.55,
    sector="Technology",
)

result = buffett.analyze(ctx)
print(f"Signal: {result.signal.value}, Score: {result.score}/10")
```

## REST API

```bash
# Start the server
python -m dashboard.app --port 8000

# Get persona info
curl http://localhost:8000/api/persona/buffett

# Run full analysis (all 18 masters) and extract single persona result
curl http://localhost:8000/api/analyze/AAPL | jq '.agents[] | select(.agent_id=="buffett")'
```

## MCP Server (Claude Desktop)

```json
{
  "mcpServers": {
    "augur": {
      "command": "python",
      "args": ["-m", "augur.mcp_server"],
      "env": { "AUGUR_DEFAULT_PERSONA": "buffett" }
    }
  }
}
```

## Skills (Hermes / Open Claw)

Each persona has a standalone Skill at `skills/<persona_id>/SKILL.md`. Copy only the one you need:

```bash
# Install a single persona skill in Hermes
hermes skills install ./skills/buffett/SKILL.md --name buffett

# Or for Open Claw
cp -r ./skills/buffett /your/openclaw/skills/
```

## inject-soul (Embed in any agent)

```bash
# Generate a soul file for Hermes
augur inject-soul --profile buffett-advisor --persona buffett \
  --format hermes --output-dir ~/.hermes/profiles/

# Generate raw markdown for any system prompt
augur inject-soul --profile buffett-advisor --persona buffett \
  --format raw --output-dir ./
```

## Custom Wrapper for Any Framework

```python
from augur.registry import AgentRegistry
from augur.personas.base import MarketContext

class AugurPersonaTool:
    def __init__(self, persona_id="buffett"):
        self.agent = AgentRegistry().get(persona_id)

    def analyze(self, ticker, **kwargs):
        try:
            from augur.data import fetch_market_context
            ctx = fetch_market_context(ticker)
        except Exception:
            ctx = MarketContext(ticker=ticker.upper(), **kwargs)
        result = self.agent.analyze(ctx)
        return {
            "signal": result.signal.value,
            "score": result.score,
            "reasoning": result.reasoning,
        }
```

## Available Persona IDs

| ID | Name | Style |
|----|------|-------|
| `buffett` | Warren Buffett | Value / Moat |
| `graham` | Benjamin Graham | Deep Value / Safety Margin |
| `munger` | Charlie Munger | Multi-disciplinary / Inverse |
| `fisher` | Philip Fisher | Growth / Scuttlebutt |
| `lynch` | Peter Lynch | GARP |
| `cathie_wood` | Cathie Wood | Disruptive Innovation |
| `dalio` | Ray Dalio | All-Weather Macro |
| `soros` | George Soros | Reflexivity |
| `marks` | Howard Marks | Cycles / Contrarian |
| `thiel` | Peter Thiel | 0-to-1 Monopoly |
| `aschenbrenner` | Leopold Aschenbrenner | AGI Infrastructure |
| `arps` | Martin Arps | Technical / Momentum |
| `dayu` | BTCdayu | Crypto Narrative / Sentiment |
| `serenity` | Serenity | Quant / Volatility |
| `duan_yongping` | Duan Yongping | Benfen / Concentration |
| `zhang_lei` | Zhang Lei (Hillhouse) | Structural Value |
| `li_lu` | Li Lu (Himalaya) | China Value |
| `dan_bin` | Dan Bin (OHP) | Brand Moat / Long-term |

---

*Related docs: [agent-integration-guide.md](agent-integration-guide.md), [hermes-setup-guide.md](hermes-setup-guide.md). For educational purposes only, not investment advice.*
