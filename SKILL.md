---
name: augur
description: "Augur — 17位虚拟投资大师多智能体共识分析系统。输入股票代码和财务数据，获得巴菲特、格雷厄姆、段永平、张磊等17位投资大师的独立评分与加权共识信号。覆盖美股/港股/A股/Crypto。"
version: 3.4.0
author: lanzhihao1986@gmail.com
license: MIT
platforms: [linux, macos, windows]
model:
  default: claude-sonnet-4-6
  alternatives: [deepseek-v3, gpt-4o, kimi-latest]
metadata:
  augur:
    type: multi-agent-consensus
    agent_count: 17
    personas: [buffett, graham, lynch, dalio, munger, soros, marks, cathie_wood, fisher, arps, aschenbrenner, dayu, thiel, duan_yongping, zhang_lei, li_lu, dan_bin]
    coverage: [US stocks, HK stocks, A shares, Crypto]
compatibility: "Python 3.8+, FastAPI dashboard 可选"
---

# Augur — 多智能体投资分析系统

## 系统概览

Augur 是一个 **17位虚拟投资大师的多智能体分析系统**。每位投资人都有独立的人格、哲学框架、行为规范和评分逻辑，系统最终用多Agent共识机制（行业加权、机制感知、相关性惩罚）汇总出集体判断。

你可以：
1. **单个投资人分析** — `augur-buffett`、`augur-zhang-lei` 等独立 Skill
2. **多Agent共识** — 全部17位大师同时分析，给出加权共识信号
3. **部署到任意平台** — Telegram、Slack、WeChat、Claude、Hermes 都支持

---

## 17位投资大师

| Skill名称 | 投资人 | 风格 | 适合场景 | 推荐模型 |
|-----------|--------|------|---------|---------|
| `augur-buffett` | Warren Buffett | 护城河价值投资 | 蓝筹、消费、金融 | claude-sonnet-4-6 |
| `augur-graham` | Benjamin Graham | 深度价值/安全边际 | 低估、破净、周期底 | claude-sonnet-4-6 |
| `augur-munger` | Charlie Munger | 格栅理论 | 跨学科分析、复杂企业 | claude-sonnet-4-6 |
| `augur-lynch` | Peter Lynch | GARP/PEG | 消费成长、行业轮动 | claude-sonnet-4-6 |
| `augur-dalio` | Ray Dalio | 宏观/全天候 | 宏观对冲、地缘 | claude-sonnet-4-6 |
| `augur-soros` | George Soros | 反身性/宏观交易 | 危机、货币、做空 | claude-sonnet-4-6 |
| `augur-marks` | Howard Marks | 周期/逆向 | 周期底部、风险管理 | claude-sonnet-4-6 |
| `augur-cathie-wood` | Cathie Wood | 颠覆性创新 | AI、生物、区块链 | claude-sonnet-4-6 |
| `augur-fisher` | Philip Fisher | 成长股/闲聊法 | 科技、细分成长 | claude-sonnet-4-6 |
| `augur-thiel` | Peter Thiel | 从0到1/垄断 | 科技垄断、平台 | claude-sonnet-4-6 |
| `augur-arps` | ARPS | Crypto/黄金宏观 | 数字资产、避险 | claude-sonnet-4-6 |
| `augur-aschenbrenner` | Leopold Aschenbrenner | AI地缘政治 | AI算力、半导体 | claude-opus-4-7 |
| `augur-dayu` | 大宇 (BTCdayu) | 信息差/情绪动量 | Crypto、Meme | deepseek-v3 |
| `augur-duan-yongping` | 段永平 | 本分/极度集中 | 消费电子、平台 | deepseek-v3 |
| `augur-zhang-lei` | 张磊 (高瓴) | 结构性价值 | 消费升级、医疗 | deepseek-v3 |
| `augur-li-lu` | 李录 (喜马拉雅) | 深度价值/安全边际 | 低估蓝筹、亚洲 | claude-sonnet-4-6 |
| `augur-dan-bin` | 但斌 (东方港湾) | 品牌护城河/时代β | 中国消费品牌 | kimi-latest |

---

## 调用方式

### 方式一：在 Hermes / Claude / OpenClaw 中调用

```
# 加载主 Skill（17位大师共识）
/skill augur
"分析 AAPL，PE=32，毛利率46%，ROE=55%，科技板块"

# 或加载单个投资人
/skill augur-buffett
"用巴菲特框架分析可口可乐 KO，当前PE=26"

/skill augur-zhang-lei
"张磊视角分析拼多多PDD，营收增速86%，毛利率62%"
```

### 方式二：API 调用

```bash
# 启动本地服务
python3 -m dashboard.app --port 8000 --cors

# 多Agent共识分析
curl "http://localhost:8000/api/analyze/NVDA?pe=45&gross_margins=0.75&roe=0.85&revenue_growth=0.78&sector=Technology"

# 单投资人详情
curl "http://localhost:8000/api/persona/buffett"
```

### 方式三：CLI 直接调用

```bash
pip install -e .
python3 -m augur.cli analyze AAPL --pe 32 --gross-margins 0.46 --roe 0.55
python3 -m augur.cli analyze AAPL --persona buffett  # 单投资人
python3 scripts/sec_holdings.py buffett zhang_lei li_lu  # 实时13F持仓
```

### 方式四：部署到 Telegram / Slack / WeChat

```bash
# Telegram Bot
export TELEGRAM_TOKEN=your_token
export AUGUR_API_URL=http://your-server:8000
python3 bots/telegram_bot.py

# 用户在 Telegram 发送：
# /analyze AAPL pe=32 gm=46 roe=55
```

---

## 配置模型

每个 Agent 可独立指定 LLM 模型，编辑 `config/agents.yaml`：

```yaml
per_agent:
  duan_yongping: deepseek-v3    # 段永平用 DeepSeek（中文更准）
  dan_bin: kimi-latest           # 但斌用 Kimi
  aschenbrenner: claude-opus-4-7 # AI地缘政治用最强模型
  buffett: claude-sonnet-4-6     # 默认
```

支持：`claude-*`, `gpt-4o*`, `deepseek-v3/r1`, `kimi-latest`, `minimax-01`，以及任何兼容 OpenAI 接口的本地模型。

---

## 共识机制说明

所有17位Agent分析完成后，系统用 `DecisionCoordinator` 计算共识：

1. **行业感知权重** — 科技股给 Aschenbrenner/Wood 更高权重，消费股给 Buffett/Munger 更高权重
2. **市场机制路由** — 熊市时 Marks/Dalio 权重提升，牛市时 Lynch/Fisher 权重提升
3. **滚动 IC 权重** — 历史预测准确率高的 Agent 动态加权
4. **多样性相关性惩罚** — 观点高度相似的 Agent 减少冗余权重
5. **Kelly 仓位建议** — 基于共识信号和置信度给出建议仓位比例
6. **风险管理否决层** — 高负债 + 熊市信号时可否决共识看多

---

## 独立 Skill 目录

```
augur/
└── skills/
    ├── buffett/SKILL.md
    ├── graham/SKILL.md
    ├── munger/SKILL.md
    ├── zhang_lei/SKILL.md
    ├── li_lu/SKILL.md
    ├── duan_yongping/SKILL.md
    ├── dan_bin/SKILL.md
    └── ... (17个，可独立安装)
```

每个独立 Skill 可单独安装到任何 agentskills.io 兼容平台：

```bash
# 只安装巴菲特 Agent
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/buffett

# 只安装中国投资人组合
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/zhang_lei
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/li_lu
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/duan_yongping
hermes skills install https://github.com/BruceLanLan/augur/tree/main/skills/dan_bin
```
