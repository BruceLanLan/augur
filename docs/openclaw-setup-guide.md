[🇺🇸 English](en/openclaw-setup-guide.md) | 🇨🇳 中文

# OpenClaw 接入 Augur — 完整指引

> Augur 通过 MCP（Model Context Protocol）向 OpenClaw 暴露 9 个工具和 19 个技能。
> 配置完成后，在 OpenClaw 里直接呼唤"巴菲特"或运行 `/skill augur-buffett` 即可。

---

## 前置条件

- OpenClaw ≥ 0.8（支持 MCP 技能注册）
- Python 3.9+ 已安装
- Augur 已克隆并安装

```bash
git clone https://github.com/BruceLanLan/augur-next.git augur
cd augur
pip install -e ".[data]"

# 验证
augur mcp-server   # 无报错则正常（Ctrl+C 退出）
```

---

## 方式一：MCP Server 接入（推荐）

OpenClaw 通过 stdio 调用 `augur mcp-server`，自动注册所有 9 个工具。

### Step 1 — 编辑 OpenClaw 配置

通常在 `~/.openclaw/config.yaml`：

```yaml
mcp_servers:
  augur:
    command: augur
    args: [mcp-server]
    description: "Augur — 18位投资大师多Agent共识分析"
    env:
      AUGUR_LOG_LEVEL: "WARNING"   # 减少 stdio 噪音
```

或通过 OpenClaw Web UI **Settings → MCP Servers → Add**，填入：

| 字段 | 值 |
|------|-----|
| Name | `augur` |
| Command | `augur` |
| Args | `mcp-server` |

### Step 2 — 验证工具注册

重启 OpenClaw 后，在聊天框输入：

```
/tools list
```

应看到 9 个 `mcp_augur_*` 工具：

```
mcp_augur_analyze      — 单个或全部大师分析
mcp_augur_consensus    — 加权共识 + Kelly 仓位
mcp_augur_committee    — 投资委员会
mcp_augur_debate       — 结构化多空辩论
mcp_augur_fetch        — 实时行情（yfinance）
mcp_augur_sentiment    — 社交情绪（StockTwits + 新闻）
mcp_augur_list_personas — 列出所有大师
mcp_augur_configure    — 配置大师模型参数
mcp_augur_create_persona — 创建自定义大师
```

### Step 3 — 开始使用

```
# 基础分析
分析一下 NVDA，用巴菲特的视角

# 委员会
召集经典价值派委员会（巴菲特、格雷厄姆、芒格、费雪）讨论 TSLA

# 共识
给我 AAPL 的多大师加权共识和 Kelly 仓位建议
```

---

## 方式二：技能（Skill）注册

Augur 提供 19 个预构建 Hermes/OpenClaw 技能，每位大师一个独立技能。
技能文件在 `skills/` 目录中。

### 一键注册所有技能

```bash
# 在 augur 目录下
openclaw skill install ./skills/augur-buffett
openclaw skill install ./skills/augur-munger
# ... 或批量：
for d in skills/augur-*; do openclaw skill install "$d"; done
```

### 单独使用某位大师

```
/skill augur-buffett AAPL
/skill augur-dalio TSLA
/skill augur-committee NVDA --preset value
```

### 技能目录

| 技能名 | 大师 | 流派 |
|--------|------|------|
| `augur-buffett` | Warren Buffett | 经典价值 |
| `augur-graham` | Benjamin Graham | 经典价值 |
| `augur-munger` | Charlie Munger | 经典价值 |
| `augur-fisher` | Philip Fisher | 经典价值 |
| `augur-lynch` | Peter Lynch | 成长 |
| `augur-cathie-wood` | Cathie Wood | 创新 |
| `augur-thiel` | Peter Thiel | 反共识 |
| `augur-aschenbrenner` | Leopold Aschenbrenner | AGI/算力 |
| `augur-dalio` | Ray Dalio | 宏观 |
| `augur-soros` | George Soros | 宏观 |
| `augur-marks` | Howard Marks | 宏观 |
| `augur-arps` | ARPS | 实际利率 |
| `augur-duan-yongping` | 段永平 | 中国价值（全中文）|
| `augur-zhang-lei` | 张磊（高瓴）| 中国价值（全中文）|
| `augur-li-lu` | 李录（喜马拉雅）| 中国价值（全中文）|
| `augur-dan-bin` | 但斌（东方港湾）| 中国价值（全中文）|
| `augur-dayu` | 大宇 BTCdayu | Crypto 情绪 |
| `augur-serenity` | Serenity | AI 供应链 |
| `augur-committee` | 投资委员会 | 多大师裁决 |

---

## 方式三：`.mcp.json` 自动发现

在项目根目录放一个 `.mcp.json`，OpenClaw / Claude Code 自动发现：

```json
{
  "mcpServers": {
    "augur": {
      "command": "augur",
      "args": ["mcp-server"]
    }
  }
}
```

Augur 安装时已在仓库根部署此文件，克隆后即生效。

---

## 常见问题

### `augur: command not found`

```bash
# 确认 pip 安装了入口点
pip install -e ".[data]"
which augur        # 应显示路径
augur --version    # 应显示版本号
```

如果在虚拟环境内，确保 OpenClaw 调用的 Python 环境与 augur 安装环境一致：

```yaml
# ~/.openclaw/config.yaml
mcp_servers:
  augur:
    command: /path/to/.venv/bin/augur
    args: [mcp-server]
```

### 工具调用超时

默认 Augur 每次分析需要 5-30 秒（取决于大师数量）。在 OpenClaw 配置中延长超时：

```yaml
mcp_servers:
  augur:
    command: augur
    args: [mcp-server]
    timeout: 120   # 秒
```

### 中国大师回复英文

中国大师（段永平、张磊、李录、但斌）默认全中文回复。如果 OpenClaw 传入英文 system prompt 覆盖了语言设置，在技能配置里强制语言：

```yaml
skills:
  augur-duan-yongping:
    system_language: zh
```

### API 密钥配置

Augur 使用 Anthropic API 进行 LLM 分析。在环境变量中配置：

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# 或写入 ~/.augur/config.yaml
```

---

## 快速验证脚本

```bash
#!/bin/bash
# 验证 Augur MCP 工具列表
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | augur mcp-server 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
tools = d.get('result', {}).get('tools', [])
print(f'✅ {len(tools)} tools registered:')
for t in tools: print(f'  - {t[\"name\"]}')
"
```

预期输出：
```
✅ 9 tools registered:
  - mcp_augur_analyze
  - mcp_augur_consensus
  - mcp_augur_committee
  ...
```

---

*For Hermes Agent setup, see [hermes-setup-guide.md](hermes-setup-guide.md)*
