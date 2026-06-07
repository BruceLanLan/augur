🇨🇳 中文 | [🇺🇸 English](README_EN.md)

<div align="center">

# 🦉 Augur Next

**你的 AI 投资委员会**

*18位传奇投资人，独立思考，一次共识*

[![v9.0.2](https://img.shields.io/badge/v9.0.2-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur-next)
[![18 Agents](https://img.shields.io/badge/18-独立_Agent-brightgreen?style=for-the-badge)](#-18位独立-agent)
[![MCP Ready](https://img.shields.io/badge/MCP-Hermes_%2F_Claude-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

> **稳定版本 → [augur](https://github.com/BruceLanLan/augur)**
> 本仓库是下一代功能的开发预览版

</div>

---

## 什么是 Augur Next？

Augur Next 将18位传奇投资人从"打分引擎"升级为**真正的独立 AI Agent**——每位大师有自己的人格、语气、决策框架和工具权限，可以通过 Hermes Studio 或 Claude Desktop 直接对话。

```
稳定版 (augur)              开发版 (augur-next)
────────────────           ────────────────────
Dashboard 评分表    →      18位独立 Agent 对话
批量共识分析        →      投资委员会辩论
模板聊天回复        →      真实 LLM 人格对话
```

---

## 🚀 5 分钟上手

### 第一步：安装

```bash
git clone https://github.com/BruceLanLan/augur-next.git && cd augur-next
pip install -e ".[data]"
# 现在 augur-mcp 命令可用
```

### 第二步：配置 Hermes Studio

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  augur:
    command: augur-mcp
```

或者 Claude Desktop：

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "augur": { "command": "augur-mcp" }
  }
}
```

### 第三步：开始对话

```
# 在 Hermes Studio 中
/skill augur-buffett
"AAPL 现在值得买吗？PE=32，ROE=55%，科技板块"

/skill augur-duan-yongping
"你怎么看腾讯的商业模式？"

/skill augur-committee
"召开价值委员会，讨论茅台的投资价值"
```

---

## 🎭 18位独立 Agent

每位 Agent 有完整的人格定义、决策框架和工具权限。

### 经典价值派

| Skill 名称 | 投资人 | 核心框架 | 语言 |
|-----------|--------|---------|------|
| `augur-buffett` | Warren Buffett | 护城河 · 长期持有 | English |
| `augur-graham` | Benjamin Graham | 安全边际 · 深度价值 | English |
| `augur-munger` | Charlie Munger | 格栅思维 · 逆向 | English |
| `augur-fisher` | Philip Fisher | 闲聊法 · 成长质量 | English |

### 成长与创新派

| Skill 名称 | 投资人 | 核心框架 | 语言 |
|-----------|--------|---------|------|
| `augur-lynch` | Peter Lynch | GARP · PEG | English |
| `augur-cathie-wood` | Cathie Wood | 颠覆创新 · Wright定律 | English |
| `augur-thiel` | Peter Thiel | 0→1 垄断 · 秘密 | English |
| `augur-aschenbrenner` | Leopold Aschenbrenner | AGI基础设施 · 地缘 | English |

### 宏观与周期派

| Skill 名称 | 投资人 | 核心框架 | 语言 |
|-----------|--------|---------|------|
| `augur-dalio` | Ray Dalio | 全天候 · 债务周期 | English |
| `augur-soros` | George Soros | 反身性 · 宏观交易 | English |
| `augur-marks` | Howard Marks | 钟摆情绪 · 二阶思考 | English |
| `augur-arps` | ARPS | 实际利率 · 黄金/Crypto | English |

### 🇨🇳 中国投资人（全中文对话）

| Skill 名称 | 投资人 | 核心框架 |
|-----------|--------|---------|
| `augur-duan-yongping` | 段永平 | 本分 · 极度集中 |
| `augur-zhang-lei` | 张磊（高瓴） | 结构性长期价值 |
| `augur-li-lu` | 李录（喜马拉雅） | 深度价值 · 安全边际 |
| `augur-dan-bin` | 但斌（东方港湾） | 品牌护城河 · 时代Beta |

### 特殊策略

| Skill 名称 | 投资人 | 核心框架 | 语言 |
|-----------|--------|---------|------|
| `augur-dayu` | 大宇 (BTCdayu) | 信息差 · 情绪动量 | English |
| `augur-serenity` | Serenity | AI供应链瓶颈 | English |

---

## 🏛️ 投资委员会模式

### 方式一：通过 Hermes Agent

```
/skill augur-committee
"价值委员会 NVDA —— 巴菲特、芒格、格雷厄姆、费雪，PE=35，AI芯片龙头"

"中国价值委员会 茅台 —— 段永平、张磊、李录、但斌，当前估值合理吗？"
```

### 方式二：通过 Dashboard

```bash
python3 -m dashboard.app
# 打开 http://localhost:8000/committee
# 选择参会大师 → 输入标的 → 看独立意见 + 裁决
```

### 方式三：通过 MCP 工具（API）

```python
# 在任何支持 MCP 的客户端里
mcp_augur_committee(
    ticker="AAPL",
    question="护城河是否正在变窄？",
    agents="buffett,munger,duan_yongping,li_lu"
)
```

---

## 🔌 MCP 工具（9个）

| 工具 | 用途 |
|------|------|
| `mcp_augur_analyze` | 单个或全部大师分析 |
| `mcp_augur_consensus` | 加权共识 + Kelly 仓位 |
| `mcp_augur_committee` | 投资委员会（独立意见+裁决，自动存历史） |
| `mcp_augur_debate` | 多轮辩论 |
| `mcp_augur_fetch` | 实时行情数据 |
| `mcp_augur_sentiment` | 社交情绪分析（StockTwits+新闻） |
| `mcp_augur_list_personas` | 列出所有18位大师 |
| `mcp_augur_configure` | 配置大师模型参数 |
| `mcp_augur_create_persona` | 无代码创建自定义大师 |

**自动发现**：项目根目录的 `.mcp.json` 让 Claude Code / 任意 MCP 客户端自动发现所有工具。

---

## 💻 CLI 命令

```bash
# 分析
augur analyze AAPL                     # 18位大师共识
augur analyze AAPL --persona buffett   # 单个大师
augur consensus NVDA                   # 加权共识 + Kelly 仓位

# 实时监控
augur serve --port 8000 --open         # 启动 Dashboard，自动打开浏览器
augur watch AAPL NVDA TSLA             # 实时监控（60s 刷新）
augur watch NVDA --alert-above 7.5     # 评分超阈值时提醒

# 组合管理
augur portfolio AAPL NVDA TSLA         # 组合 Kelly 配置建议
augur watchlist-add AAPL               # 添加到自选股
augur backtest AAPL --days 30          # 历史回测

# Agent 系统
augur-mcp                              # 启动 MCP server（Hermes/Claude接入）
augur skills                           # 列出所有 Agent Skill
augur skills --school value            # 按流派筛选
augur inject-soul --persona buffett    # 导出 Agent Soul 到文件

# 消息推送
augur telegram                         # 启动 Telegram Bot
augur slack                            # 启动 Slack Bot
```

---

## 📊 Dashboard（Web 界面）

```bash
augur serve                    # 最简启动
augur serve --port 8080        # 自定义端口
docker compose up              # Docker 一键启动
```

18个页面：仪表盘 / 股票 / 信号 / 扫描 / 自选股 / 持仓 / 回测 / AI 对话 / 组合优化 / **委员会** / 对决 / 辩论 / 历史 / 排行 / 人格 / **Hermes 接入指南** / 创建大师 / 设置

---

## 🎨 高度 DIY — 自定义大师

```bash
# 方式一：Dashboard 无代码创建（推荐）
augur serve → 访问 /create-persona

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

# 方式三：修改 soul.py 后重新生成所有 Skill
python3 scripts/generate_skills.py

# 方式四：直接通过 MCP 创建
mcp_augur_create_persona(yaml_content="agent_id: ...")
```

---

## 与稳定版的关系

| 功能 | augur (稳定 v8.2.x) | augur-next (开发 v9.0.x) |
|------|---------------------|--------------------------|
| Dashboard | ✅ 完整 18页 | ✅ + Committee + Hermes Setup |
| MCP Server | 7个工具 | **9个工具**（+committee +sentiment +create） |
| Hermes / OpenClaw Skill | ❌ | **19个 SKILL.md + manifest.json** |
| Agent System Prompt | 通用模板 | **专属人格化 prompt，中国4位全中文** |
| `augur-mcp` 命令 | ❌ | ✅ |
| `.mcp.json` 自动发现 | ❌ | ✅ |
| `augur serve/watch/skills/portfolio` | ❌ | ✅ |
| 一键安装脚本 | ❌ | ✅ `install.sh` |

---

---

## 📝 版本日志

<details>
<summary><strong>v9.0.2 — 预设委员会 / sentiment MCP / 专属 Agent Prompt (current)</strong></summary>

- **预设委员会**：经典价值 / 中国价值 / 宏观全天候 / 创新成长 / 全体委员会 一键加载。
- **augur_sentiment MCP 工具**（第9个工具）：社交情绪分析 StockTwits + 新闻，直接从 MCP 客户端调用。
- **18位专属 Agent System Prompt**：每位大师有完整的人格化 system prompt，中国4位全中文。
- **augur-next README**：全面重写，讲清 v9.0 的 Agent 委员会定位。
</details>

<details>
<summary><strong>v9.0.1 — 18位专属 Hermes Agent Skill</strong></summary>

- 18+1 个 `skills/augur-*/SKILL.md`，augur-committee 委员会协调者。
- augur_committee MCP 工具（结构化委员会流程）。
- augur-mcp console script。
- Dashboard /committee 页面。
</details>

---

<div align="center">
MIT License · Built by <a href="https://github.com/BruceLanLan">BruceLanLan</a> · 开发预览版，API 可能变动

*仅供学习研究，不构成投资建议*
</div>
