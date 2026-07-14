🇨🇳 中文 | [🇺🇸 English](README_EN.md)

<div align="center">

<img src="docs/images/zh/hero-banner.png" alt="Augur — 你的 AI 投资决策委员会" width="100%">

# 🦉 Augur

**18 位传奇投资人，同时分析同一支股票，给出一个共识裁决。**

把 Warren Buffett、Ray Dalio、段永平、Cathie Wood 放在同一个房间——他们不会同意对方的观点。这正是重点。

[![v10.13.0](https://img.shields.io/badge/v10.13.0-Latest-ff6b35?style=for-the-badge)](https://github.com/BruceLanLan/augur/releases)
[![2449 Tests](https://img.shields.io/badge/2449_Tests-Passing-brightgreen?style=for-the-badge)](https://github.com/BruceLanLan/augur/actions)
[![SEC EDGAR](https://img.shields.io/badge/SEC_EDGAR-真实财报数据-4a90d9?style=for-the-badge)](#-18位投资大师)
[![18 大师](https://img.shields.io/badge/18-投资大师-gold?style=for-the-badge)](#-18位投资大师)
[![MCP Ready](https://img.shields.io/badge/MCP-Claude_%2F_Hermes-orange?style=for-the-badge)](https://modelcontextprotocol.io)
[![PWA](https://img.shields.io/badge/PWA-可安装应用-blue?style=for-the-badge)](#-dashboard-web-界面)
[![MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

</div>

---

## 🚀 30秒上手

```bash
git clone https://github.com/BruceLanLan/augur.git && cd augur
pip install -e ".[data]"
augur serve --open          # 打开 Dashboard
```

或者直接在命令行：

```bash
augur analyze AAPL          # 18位大师同时分析
augur consensus NVDA        # 加权共识 + Kelly 仓位建议
augur workflow TSLA         # 一次调用跑完整分析链
```

---

## ✨ v10.0 有什么新的

<img src="docs/images/screenshots/dashboard-hd2d.png" alt="Augur v10 首页 — 实时行情 + Bloomberg 风格终端" width="100%">

### 你的专属 Bloomberg 终端

**`/settings` 页面现在是一个完整的终端配置系统：**

<img src="docs/images/screenshots/workspace-profiles.png" alt="Terminal Workspace — 多套 Profile 保存切换" width="100%">

- **4 套布局预设**：analyst / trader / committee / minimal，一键切换首页和工具栏
- **多套命名 Profile**：保存"白天看盘"和"周末研究"两套配置，互不影响
- **启用大师子集**：只让你信任的几位大师参与共识，权重自动重归一化
- 配置保存在 `~/.augur/workspace.yaml`，换机器也能带走

### AI Agent 现在能操作你的终端

不只是"聊天"——你的 Claude / Hermes Agent 现在可以直接**读取并修改**你的 Augur 工作区：

```python
# Claude Desktop / Hermes 里直接调用：
mcp_augur_workspace_get()                       # 查看当前布局和启用的大师
mcp_augur_workspace_set(layout_preset="trader") # 切换到 trader 模式
mcp_augur_workspace_profiles()                  # 管理你的所有 Profile
```

### 一次调用跑完整分析链

```bash
augur workflow NVDA --steps fetch,analyze,consensus,committee
```

`fetch → analyze → consensus → committee → debate → sentiment` 六步流水线，单步失败不中断，步骤跟随你的 Profile 自动调整。

---

## 📊 Dashboard 全貌

<img src="docs/images/screenshots/personas-hd2d.png" alt="18位投资大师 — 四大流派" width="100%">

### 股票分析

<img src="docs/images/screenshots/report-hd2d.png" alt="股票分析页 — 输入 Ticker 召唤18位大师" width="100%">

输入任意股票代码（A股 / 美股 / 港股），18位大师同时给出：
- **Augur 评分**（0–10）+ **BUY / NEUTRAL / SELL** 信号
- **Kelly 仓位建议**（基于加权共识置信度）
- **The Oracle of Augur**：一句话裁决
- 多空分布：`13 Bullish / 5 Neutral / 0 Bearish`

### 投资委员会

<img src="docs/images/screenshots/committee-hd2d.png" alt="投资委员会 — 预设组合 + 独立意见 + 最终裁决" width="100%">

五套预设委员会，也可以自由组合：
- **经典价值**：Buffett · Graham · Munger · Fisher
- **中国价值**：段永平 · 张磊 · 李录 · 但斌
- **宏观全天候**：Dalio · Soros · Marks · ARPS
- **创新成长**：Cathie Wood · Thiel · Aschenbrenner · Lynch
- **全体委员会**：18位全部出席

### 多空辩论

<img src="docs/images/screenshots/04-bullish-critical.png" alt="结构化辩论 — 多空双方自动交锋" width="100%">

选 2–4 位大师就同一标的展开多轮辩论，自动生成完整的多头和空头论据。

### 历史记录

<img src="docs/images/screenshots/history.png" alt="分析历史 — GitHub 风格热力图 + 详细记录" width="100%">

每次分析自动存档，GitHub 风格 52 周热力图，按信号 / 评分 / 日期筛选。

### 对比分析

<img src="docs/images/screenshots/compare-radar.png" alt="对比分析 — 5维度评分雷达图 + 因子明细" width="100%">

选 2–5 位大师同台对比同一标的，5 维度（估值 / 成长 / 质量 / 动量 / 安全）雷达图一眼看出分歧所在，展开明细表可看到每位大师用了哪些具体因子（PE、护城河、动量等）打出这个分数。

### Hermes Agent 接入

<img src="docs/images/screenshots/hermes-setup.png" alt="Hermes Agent 接入指南 — MCP 一键配置" width="100%">

一步步配置指南：安装 MCP 服务、注册 Claude Desktop / Hermes，把 18 位大师和委员会都接进你的 AI Agent 工作流。

---

## 🎭 18位投资大师

> 4 大流派，覆盖价值 / 成长 / 宏观 / 中国市场。中国大师**全程中文对话**。

| 流派 | 大师 |
|------|------|
| 🏦 经典价值 | Warren Buffett · Benjamin Graham · Charlie Munger · Philip Fisher |
| 🚀 成长创新 | Peter Lynch · Cathie Wood · Peter Thiel · Leopold Aschenbrenner |
| 🌍 宏观周期 | Ray Dalio · George Soros · Howard Marks · ARPS Crypto/Gold |
| 🇨🇳 中国价值 | 段永平 · 张磊（高瓴）· 李录（喜马拉雅）· 但斌（东方港湾）· 大宇 BTCdayu |
| ⚙️ 特殊策略 | Serenity（AI算力供应链）|

每位大师都有独立的 [Hermes Skill](src/skills/)，可直接在 Hermes Studio 里单独对话。

---

## 🔌 接入任意平台

| 平台 | 接入方式 |
|------|---------|
| **Web Dashboard** | `augur serve` |
| **Claude Desktop** | MCP 配置 → `augur mcp-server` |
| **Hermes Agent** | `/skill augur-buffett` |
| **Claude Code** | `.mcp.json` 自动发现（克隆即用） |
| **OpenClaw** | YAML manifest 自动注册 |
| **Telegram / Slack** | `augur telegram` / `augur slack` |

### MCP 13个工具

```json
// Claude Desktop (~/.config/claude/claude_desktop_config.json)
{
  "mcpServers": {
    "augur": { "command": "augur", "args": ["mcp-server"] }
  }
}
```

| 工具 | 用途 |
|------|------|
| `mcp_augur_analyze` | 单个或全部大师分析 |
| `mcp_augur_consensus` | 加权共识 + Kelly 仓位 |
| `mcp_augur_committee` | 投委会（独立意见 + 裁决） |
| `mcp_augur_debate` | 多轮结构化辩论 |
| `mcp_augur_workflow` | 完整分析流水线 |
| `mcp_augur_workspace_get` | 🆕 读取你的终端配置 |
| `mcp_augur_workspace_set` | 🆕 修改你的终端配置 |
| `mcp_augur_workspace_profiles` | 🆕 管理 Profile |
| `mcp_augur_fetch` | 实时行情 |
| `mcp_augur_sentiment` | 社交情绪分析 |
| `mcp_augur_create_persona` | 创建自定义大师 |
| `mcp_augur_list_personas` | 列出全部大师 |
| `mcp_augur_configure` | 配置模型参数 |

---

## 💻 CLI 完整命令

```bash
# 分析
augur analyze AAPL                              # 18位大师共识
augur analyze AAPL --persona buffett            # 单个大师
augur consensus NVDA                            # 加权共识 + Kelly 仓位
augur report AAPL -o report.md                  # 生成深度分析报告
augur committee AAPL -q "护城河是在变宽还是变窄？" # 投资委员会
augur chat AAPL --persona buffett               # 快速对话
augur workflow TSLA --steps fetch,analyze,consensus,committee

# 数据
augur fetch AAPL                                # 实时行情 + 财务指标
augur sentiment AAPL                            # 社交情绪分析
augur guidance AAPL                             # AI 提炼管理层展望（默认关闭，见下文）

# Dashboard
augur serve --port 8000 --open                  # 启动并自动打开浏览器

# 监控
augur watch AAPL NVDA TSLA                      # 60s 刷新
augur watch NVDA --alert-above 7.5             # 评分超阈值提醒

# 组合与回测
augur portfolio AAPL NVDA TSLA                 # Kelly 配置建议
augur backtest AAPL --days 30                  # 真实历史数据回测
augur ic-report                                # Agent IC 排行榜

# 自选股 + 定时任务
augur watchlist-add AAPL --pe 30 --roe 0.55
augur watchlist-show
augur cron-run                                  # 手动跑一次自选股分析
augur cron-start                                # 启动定时调度守护进程

# Agent
augur mcp-server                               # 启动 MCP server（stdio）
augur skills                                   # 列出所有 Skill
augur skills --school value                    # 按流派筛选
augur inject-soul -p my_profile --persona buffett  # 把大师人格注入到某个 Agent 配置

# Bot
augur telegram / augur slack / augur wechat / augur lark

# 更新
augur update                                    # git pull + 重装（仅 git clone 安装适用）

# 排障
augur doctor                                    # 环境自检：SSL/TLS、API key、数据源连通性、学习数据积累进度
augur doctor --offline                          # 同上，但跳过真实网络请求
```

---

## 🎨 创建专属大师

```bash
# 方式一：Dashboard 无代码构建器
augur serve
# 访问 http://localhost:8000/create-persona

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
augur analyze AAPL --persona my_quant

# 方式三：MCP 工具
mcp_augur_create_persona(yaml_content="agent_id: ...")
```

---

## 📝 更新日志

> 非技术向用户说明见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。

<details open>
<summary><strong>v10.13.0 — 因子级归因分析（研究脚本） (current)</strong></summary>

- 🆕 **`scripts/factor_attribution.py`**：新增研究脚本，对 18 位大师 metadata 里约 70-90 个具名因子逐个计算横截面 rank-IC（哪个因子在预测未来收益上真的有用），内置"分半稳定性"检验防止多重比较假阳性（类似之前 regime 权重踩过的坑）——只有前后两段时间窗口方向一致且都够强的因子才算"稳定候选"，其余照样打印但明确标注不可信
- ✅ 2449 个测试全部通过

详见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。
</details>

<details>
<summary><strong>v10.12.0 — 每周数据源真实网络烟测</strong></summary>

- 🆕 **每周自动烟测**：新增 GitHub Actions 定时任务（每周一），对 SEC EDGAR 和 yfinance 做真实网络连通性检查——EDGAR 失败会让任务判红（SEC 很少封锁 CI 的 IP，失败是真信号），yfinance 失败只警告不判红（Yahoo 对云端 IP 的限流/封锁太常见，不代表真的坏了）
- ✅ 2439 个测试全部通过

详见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。
</details>

<details>
<summary><strong>v10.11.0 — 数据源连通性历史追踪</strong></summary>

- 🆕 **`augur doctor` 新增 7 天连通性历史**：每次跑 `augur doctor` 都会把当次探测结果记到本地（`~/.augur/provider_stats.json`），累积成一条短期趋势——像 stooq 端点失效这种问题，以后会在 `augur doctor` 里显示成"0/7 reachable"，不用再靠人工偶然发现
- ✅ 2427 个测试全部通过

详见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。
</details>

<details>
<summary><strong>v10.10.0 — augur doctor 环境自检</strong></summary>

- 🆕 **`augur doctor`**：一键诊断本机环境——Python/SSL 工具链是否有已知会破坏 yfinance 的组合（如 LibreSSL）、可选 API key 配置状态、数据源连通性实测、学习引擎数据积累进度；`--offline` 跳过真实网络请求
- ✅ 2408 个测试全部通过

详见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。
</details>

<details>
<summary><strong>v10.9.0 — 可信度全面修复 + SEC EDGAR 真实数据</strong></summary>

- ✅ **共识计算不再被稀释一半**：从未验证过有效性的 MetaModel 中位数混合默认权重归零
- ✅ **回测默认真实历史数据**：Dashboard/CLI 不再默认展示合成数据（`--demo` 才用假数据，且明确标注）
- ✅ **学习机制真正开始积累数据**：预测立即持久化 + 定时任务自动核对到期预测结果
- 🆕 **SEC EDGAR 真实财报**：18位大师的 PE/ROE/毛利率等指标改用官方 10-K/10-Q 数据，历史回溯到约 2011 年（美股/中概股）
- 🆕 **内部人交易信号**：追踪高管/董事最近 90 天真实公开市场买卖
- 🆕 **机构持仓信号**：追踪伯克希尔、文艺复兴科技、桥水基金等知名机构季度持仓变化
- 🆕 **`augur guidance`**（默认关闭）：LLM 提炼最新财报管理层展望情绪 + 前瞻指引数字
- 🔧 **情绪分析修正**：剔除了一直是假数据的 X（Twitter）20% 权重
- 🔧 **Regime 权重诚实下线**：真实数据验证后发现没有明显效果，已停用未经验证的手工规则
- ✅ 2388 个测试全部通过

详见 [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md)。
</details>

<details>
<summary><strong>v10.0.0 — 终端工作区 + Agentic 工作流 + 13 MCP 工具 + WebSocket 实时推送</strong></summary>

**v8 → v10 全面升级要点：**

- 🆕 **Terminal Workspace**：Bloomberg 风格多套 Profile，布局预设，大师子集过滤，委员会预设绑定
- 🆕 **3 个工作区 MCP 工具**：Agent 可读写你的终端配置（`workspace_get/set/profiles`）
- 🆕 **`augur_workflow`**：6 步分析流水线，单步失败不中断，步骤联动 Profile
- 🆕 **WebSocket 实时推送**：`/ws/workspace` 状态广播 + `/ws/workflow` 逐步进度
- 🆕 **augur-terminal 元技能**：Hermes 统一入口，13 工具 + 15 页面 + 4 预设
- 🆕 **Hermes committee.yaml**：委员会主席 Agent 角色
- ✅ 共识引擎：行业权重 · regime 路由 · MetaModel · 点时基本面
- ✅ Dashboard：4 语言 i18n · 历史热力图 · PWA · 键盘快捷键 · CSV 导出
- ✅ 2136 个测试全部通过
</details>

<details>
<summary><strong>v10.16.x — 内部迭代（已全部包含在 v10.0.0 中）</strong></summary>

- v10.16.7：历史热力图 + Optimizer Sharpe 修复
- v10.16.6：投委会事件循环阻塞缓解
- v10.16.5：首页 11 个接口阻塞修复
- v10.16.4：投委会 Kelly 仓位显示修复
- v10.16.3：workflow 步骤联动布局预设
- v10.16.2：workflow 局部失败容错 + 工作区 ETag
- v10.16.1：MCP 工作区工具 + 委员会预设接线
</details>

<details>
<summary><strong>v9.0.x — Hermes Agent + 委员会体系</strong></summary>

- 19 个 Hermes Skill，中国大师全中文对话
- 9 个 MCP 工具（committee / sentiment / create_persona / debate）
- 委员会预设系统 + Hermes 接入指南页
- PWA 可安装 + Ticker Tape WebSocket + Chat 数据卡片
</details>

<details>
<summary><strong>v8.2.x — HD-2D 设计系统 + Optimizer + AI 对话</strong></summary>

- Markowitz 有效前沿图 · Rules→Bot 推送 · AI 对话 LLM 支持
- HD-2D 设计系统：ExecCard / OracleSays / ScorecardGrid
- WCAG AA 合规 · 线程安全 · Scanner 加固
</details>

---

<div align="center">

MIT License · Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a>

*仅供学习研究，不构成投资建议*

</div>
