<p align="center">
  <img src="https://img.shields.io/badge/13-Investor%20Personas-brightgreen?style=for-the-badge" alt="13 Personas"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-Web%20UI-teal?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Hermes%20Web%20UI-Ready-purple?style=for-the-badge" alt="Hermes Ready"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT"/>
</p>

<h1 align="center">🦉 Buffett Oracle Analyzer</h1>
<h3 align="center">让13位投资大师为你决策 — 多智能体投资分析系统</h3>

<p align="center">
  <img src="docs/images/hero-banner.svg" alt="Buffett Oracle Analyzer" width="100%"/>
</p>

<p align="center">
  <em>13位AI投资大师 · 多维度共识分析 · Bloomberg风格仪表盘</em>
</p>

<p align="center">
  <a href="#-核心功能">功能</a> ·
  <a href="#-13位投资大师">投资人</a> ·
  <a href="#-快速开始">开始使用</a> ·
  <a href="#-web-dashboard">Web界面</a> ·
  <a href="#-hermes-web-ui-整合">Hermes整合</a> ·
  <a href="#-项目架构">架构</a> ·
  <a href="#-路线图">路线图</a>
</p>

> **Warren Buffett (沃伦·巴菲特)** 会买这只股票吗？**Ray Dalio (瑞·达利欧)** 怎么看当前宏观周期？**Cathie Wood (凯西·伍德)** 的颠覆性创新框架怎么说？
>
> 不用猜。Buffett Oracle Analyzer 用13位虚拟投资大师的独立Agent，对同一标的给出各自的评分、信号和理由，再用多Agent共识机制汇总，给你一份「投资大师天团」的集体判断。

---

## ⚡ 核心功能

| 功能 | 说明 |
|------|------|
| 🧠 **13位投资大师人格** | 从价值投资到币圈博弈，每位大师都有独立的评分逻辑与分析框架 |
| 🔄 **多Agent共识机制** | 行业感知权重 + 市场机制路由 + 滚动IC动态权重 + 多样性相关性惩罚 |
| 📈 **人格进化追踪** | 追踪每位大师的持仓变化与风格漂移，动态注入分析上下文 |
| 🌐 **跨资产覆盖** | 股票、Crypto、宏观指标、稳定币 — 一个系统通吃 |
| 📊 **Web Dashboard** | Bloomberg暗色风格FastAPI界面，实时呈现分析结果 |
| 🎨 **YAML自定义人格** | 无需写代码，YAML文件即可创建你自己的投资策略Agent |
| 🔌 **Hermes Web UI整合** | 三方案支持：Skill一键安装 / 独立Web / 原生PR整合 |
| 📋 **一键共识报告** | 所有Agent分析完成后自动汇总共识评级与分歧点 |

---

## 🤖 13位投资大师

| # | 投资人 | 风格 | 核心指标 | 适合场景 |
|---|--------|------|---------|---------|
| 1 | 🏆 **Warren Buffett (沃伦·巴菲特)** | 护城河价值投资 | 毛利率>40%、ROE>15%、负债<50% | 蓝筹、消费、金融 |
| 2 | 📊 **Benjamin Graham (本杰明·格雷厄姆)** | 深度价值/安全边际 | PE<15、PB<1.5、流动比>2 | 低估、破净、周期 |
| 3 | 🚀 **Peter Lynch (彼得·林奇)** | GARP成长 | PEG<1.5、营收增速>15%、PEG/FCF | 消费、成长、行业轮动 |
| 4 | 🌐 **Ray Dalio (瑞·达利欧)** | 宏观/全天候 | 四象限分析、债务周期、风险平价 | 宏观对冲、地缘风险 |
| 5 | 🧠 **Charlie Munger (查理·芒格)** | 格栅理论/多元思维 | ROE>20%、护城河+管理层、跨学科 | 科技+传统、跨学科 |
| 6 | 🔄 **George Soros (乔治·索罗斯)** | 反身性/宏观交易 | 反身性信号、趋势动量、宏观偏差 | 危机、货币、做空 |
| 7 | 📉 **Howard Marks (霍华德·马克斯)** | 周期/逆向投资 | 周期位置、市场情绪、估值分位 | 抄底、风险管理 |
| 8 | 💡 **Cathie Wood (凯西·伍德)** | 颠覆性创新 | 营收增速>30%、研发投入、TAM | 科技、生物、新能源 |
| 9 | 🔬 **Philip Fisher (菲利普·费雪)** | 成长股/闲聊法 | 研发>10%、毛利率>50%、管理层质量 | 早期成长、细分龙头 |
| 10 | 🥇 **ARPS** | Crypto/黄金宏观 | BTC相关性、黄金避险、美元强弱 | 数字资产、避险 |
| 11 | 🤖 **Leopold Aschenbrenner (利奥波德·阿申布伦纳)** | AI地缘政治 | AI投入、算力需求、人才密度 | AI、算力、地缘政治 |
| 12 | ₿ **大宇 (BTCdayu)** | 币圈看准+重仓 | 情绪动量>估值、信息差>基本面 | Crypto、Meme、新叙事 |
| 13 | 🏢 **Peter Thiel (彼得·蒂尔)** | 从0到1垄断 | 网络效应>0、高毛利率、技术壁垒 | 垄断型科技、零到一 |

> 📖 每位投资人都有完整的人格文档（`personas/*.md`）、YAML自定义人格（`personas/custom/*.yaml`）、和Python分析Agent（`scanner/personas/*.py`）。

---

## 🧬 人格进化追踪

投资人的判断不是静态的。系统追踪每位大师的持仓变化、风格漂移与关键事件，分析时自动注入当前状态上下文。

```
巴菲特进化时间线
1965 控股伯克希尔 → 1972 See's Candies(护城河) → 1988 可口可乐
→ 2008 金融危机逆向投资 → 2016 苹果(接受科技) → 2025 CRCL(接受加密)
```

| 投资人 | 关键事件 | 风格漂移 |
|--------|---------|---------|
| **Warren Buffett (沃伦·巴菲特)** | 9个 (1965→2025) | 纯价值 → 价值+成长 → 接受加密 |
| **大宇 (BTCdayu)** | 8个 (2021→2026) | 技术分析 → 信息差 → 三重仓位 |
| 更多 | 持续更新中... | |

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/BruceLanLan/buffett-oracle-analyzer.git
cd buffett-oracle-analyzer
pip install -r requirements.txt
```

### Web Dashboard

```bash
python3 -m dashboard.app
# → 打开浏览器访问 http://localhost:8000
```

### 命令行分析

```bash
# 分析单一标的（所有13位Agent）
python3 -c "
from scanner.personas.registry import AgentRegistry
from scanner.personas.base import MarketContext

r = AgentRegistry()
ctx = MarketContext(ticker='AAPL', price=180, pe=28, revenue_growth=0.08,
                    gross_margins=0.45, roe=0.35, debt_ratio=45)

for agent in r.get_all():
    result = agent.analyze(ctx)
    print(f'{agent.name:>25}: {result.signal.value.upper():>8} ({result.score:.1f}/10)')
"
```

### 进化追踪

```bash
python3 -c "
from personas.persona_evolution import PersonaEvolutionTracker
t = PersonaEvolutionTracker()
ctx = t.get_current_context('buffett')
print('Latest events:', [e['event'] for e in ctx['latest_events']])
print('Current biases:', ctx['current_biases'])
"
```

### 自定义人格（YAML）

在 `personas/custom/` 下创建 YAML 文件即可自动注册：

```yaml
agent_id: my_quant
name: "我的量化策略"
scoring_weights:
  momentum: 0.50
  value: 0.50
factors:
  momentum:
    base: 5
    rules:
      - {if: "rsi > 60 and rsi < 75", add: 2}
      - {if: "macd > macd_signal", add: 1}
```

---

## 📊 Web Dashboard

Bloomberg风格的暗色主题Web界面，内置FastAPI服务：

```
📊 首页    — 市场总览
🤖 人格页  — 13位投资人对比
📈 分析页  — 单标的深度分析
🔄 辩论页  — Agent间模拟辩论
⚖️ 风险页  — Kelly仓位/Calmar比率
```

![Dashboard Preview](https://img.shields.io/badge/UI-Bloomberg%20Style-00ff00?style=flat-square)

*（实机截图即将上线）*

---

## 🔄 Hermes Web UI 整合

本项目可无缝集成到 [Hermes Web UI](https://github.com/EKKOLearnAI/hermes-web-ui)：

### 方案A：Skill模式（推荐，零配置）

```bash
# 一键安装
hermes skills install https://github.com/BruceLanLan/buffett-oracle-analyzer

# 在Hermes Web UI中
/skill buffett-oracle
→ "分析AAPL，使用巴菲特人格"
→ 返回13位Agent的共识分析结果
```

### 方案B：独立FastAPI + iframe嵌入

```bash
# 启动独立服务
python3 -m dashboard.app --port 8080 --cors

# 在Hermes Web UI中通过iframe嵌入
```

### 方案C：原生PR整合（进行中）

向 hermes-web-ui 提交PR，添加原生 "Investment Analysis" 页面：
- 人格选择器（13位投资大师）
- Agent评分雷达图
- 多Agent对比视图
- 历史追踪时间线
- 一键导出分析报告

### 整合路线图

```
Phase 1: ✅ Skill封装 → hermes skills install 一键安装
Phase 2: 🔄 Web UI增强 → FastAPI完善 + CORS + REST API
Phase 3: 📋 PR提交 → hermes-web-ui 原生页面
Phase 4: 🚀 联合发布 → 双项目联动宣传
```

---

## 🏗️ 项目架构

![Architecture Diagram](docs/images/architecture.svg)

```
buffett-oracle-analyzer/
│
├── scanner/                    # 分析引擎
│   ├── personas/               # 13位投资人人格Agent
│   │   ├── base.py             # Agent基类
│   │   ├── buffett.py          # Warren Buffett (沃伦·巴菲特)
│   │   ├── graham.py           # Benjamin Graham (本杰明·格雷厄姆)
│   │   ├── lynch.py            # Peter Lynch (彼得·林奇)
│   │   ├── dalio.py            # Ray Dalio (瑞·达利欧)
│   │   ├── munger.py           # Charlie Munger (查理·芒格)
│   │   ├── soros.py            # George Soros (乔治·索罗斯)
│   │   ├── marks.py            # Howard Marks (霍华德·马克斯)
│   │   ├── cathie_wood.py      # Cathie Wood (凯西·伍德)
│   │   ├── fisher.py           # Philip Fisher (菲利普·费雪)
│   │   ├── arps.py             # ARPS (Crypto/黄金)
│   │   ├── aschenbrenner.py    # Leopold Aschenbrenner (利奥波德·阿申布伦纳)
│   │   ├── dayu.py             # 大宇 (BTCdayu)
│   │   ├── peter_thiel.py      # Peter Thiel (彼得·蒂尔)
│   │   └── registry.py         # Agent注册中心
│   └── persona_loader.py       # YAML自定义人格加载
│
├── personas/                   # 投资人文档
│   ├── da-yu.md                # 大宇投资体系
│   ├── ray-dalio.md            # Ray Dalio 宏观框架
│   ├── ... (13份文档)
│   ├── custom/                 # YAML自定义人格
│   └── evolution/              # 进化追踪数据
│
├── dashboard/                  # Web UI
│   ├── app.py                  # FastAPI应用
│   └── templates/              # HTML模板
│
├── docs/                       # 文档
│   ├── hermes-web-ui-integration.md
│   └── ...
│
├── SKILL.md                    # Hermes Agent Skill
└── README.md                   # 本文件
```

---

## 📋 版本日志

| 版本 | 日期 | 内容 |
|------|------|------|
| **v2.0.4** | 2026-05-21 | 🤖 新增Peter Thiel(彼得·蒂尔)从0到1垄断投资框架 |
| **v2.0.3** | 2026-05-21 | 📝 补充3份人格文档(buffett/graham/munger) + 12位投资人进化数据全部完善 |
| **v2.0.2** | 2026-05-21 | 🏗️ 项目架构图 + 12位完整人格文档(从private版复制) |
| **v2.0.1** | 2026-05-21 | 📖 重写README(12人格完整介绍 + Hermes整合方案 + 路线图) |
| **v2.0** | 2026-05-21 | 🎉 12位完整投资人人格系统 + 完整扫描器基础设施 |
| **v1.7** | 2026-05-21 | Web UI人格页面 + Hermes Web UI整合计划文档 |
| **v1.6** | 2026-05-21 | 投资人进化追踪系统(PersonaEvolutionTracker) |
| **v1.5** | 2026-05-21 | 大宇(BTCdayu)币圈投资人格 + YAML自动加载 |
| **v1.1** | 2026-05 | 简化结构，回归单风格框架 |
| **v1.0** | - | 初始版本：巴菲特单人格分析 |

---

## 🗺️ 路线图

- [x] **v1.0-v1.5**: 巴菲特 → 大宇人格加入
- [x] **v1.6-v2.0**: 进化追踪 + 12位完整人格
- [x] **v2.0.4**: Peter Thiel (彼得·蒂尔) 垄断框架加入
- [ ] **v2.1**: 持仓数据精准化(基于SEC 13F/公开财报)
- [ ] **v2.2**: 新增中国投资人(段永平/张磊/李录/但斌)
- [ ] **v2.3**: Hermes Web UI PR整合
- [ ] **v2.4**: private版功能合并回public版
- [ ] **v3.0**: Docker容器化 + 日频数据仓库

---

## 🤝 贡献指南

欢迎通过各种方式贡献：

1. **新投资人人格** — 在 `personas/custom/` 下添加 YAML 文件即可
2. **算法优化** — 改进 `scanner/personas/` 中的评分逻辑
3. **Web UI增强** — 完善 `dashboard/` 前端界面
4. **文档** — 完善 README 和人格文档
5. **PR到Hermes Web UI** — 帮助项目与 hermes-web-ui 整合

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a></sub>
  <br>
  <sub>Special thanks to <a href="https://dayu.xyz">大宇 (BTCdayu)</a> for investment philosophy framework</sub>
</p>
