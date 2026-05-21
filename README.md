<p align="center">
  <img src="https://img.shields.io/badge/12-Investor%20Personas-brightgreen?style=for-the-badge" alt="12 Personas"/>
  <img src="https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-Web%20UI-teal?style=for-the-badge&logo=fastapi" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Hermes%20Web%20UI-Ready-purple?style=for-the-badge" alt="Hermes Ready"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT"/>
</p>

<h1 align="center">🦉 Buffett Oracle Analyzer</h1>
<h3 align="center">多智能体投资分析系统 — 12位虚拟投资大师 × AI智能分析 = 你的个人金融参谋</h3>

<p align="center">
  <a href="#-核心功能">功能</a> ·
  <a href="#-12位投资大师">投资人</a> ·
  <a href="#-快速开始">开始使用</a> ·
  <a href="#-web-ui">Web界面</a> ·
  <a href="#-hermes-web-ui-整合">Hermes整合</a> ·
  <a href="#-项目架构">架构</a> ·
  <a href="#-路线图">路线图</a>
</p>

---

## 🌟 核心功能

| 功能 | 说明 |
|------|------|
| 🤖 **12位投资大师人格** | 巴菲特、格雷厄姆、林奇、达利欧、芒格、索罗斯、马克斯、伍德、费雪、ARPS、阿申布伦纳、大宇 |
| 🧬 **人格进化追踪** | 追踪每位投资人的持仓变化、风格漂移、关键事件，动态注入分析上下文 |
| 📊 **多Agent共识机制** | 行业感知权重 + 市场机制路由 + 滚动IC动态权重 + 多样性相关性惩罚 |
| 📈 **Web Dashboard** | Bloomberg风格的FastAPI界面，实时显示分析结果 |
| 🔄 **Hermes Web UI整合** | 三方案支持：Skill模式 / 独立Web / PR整合 |
| 📝 **YAML自定义人格** | 无需写代码，YAML文件即可创建新投资人人格 |
| 🎯 **跨资产支持** | 股票、Crypto、宏观指标、稳定币全面覆盖 |

---

## 🤖 12位投资大师

| # | 投资人 | 风格 | 核心指标 | 适合场景 |
|---|--------|------|---------|---------|
| 1 | 🏆 **Warren Buffett** | 护城河价值投资 | 毛利率>40%、ROE>15%、负债<50% | 蓝筹、消费、金融 |
| 2 | 📊 **Benjamin Graham** | 深度价值/安全边际 | PE<15、PB<1.5、流动比>2 | 低估、破净、周期 |
| 3 | 🚀 **Peter Lynch** | GARP成长 | PEG<1.5、营收增速>15%、PEG/FCF | 消费、成长、行业轮动 |
| 4 | 🌐 **Ray Dalio** | 宏观/全天候 | 四象限分析、债务周期、风险平价 | 宏观对冲、地缘风险 |
| 5 | 🧠 **Charlie Munger** | 格栅理论/多元思维 | ROE>20%、护城河+管理层、跨学科 | 跨学科、科技+传统 |
| 6 | 🔄 **George Soros** | 反身性/宏观交易 | 反身性信号、趋势动量、宏观偏差 | 危机、货币、做空 |
| 7 | 📉 **Howard Marks** | 周期/逆向投资 | 周期位置、市场情绪、估值分位 | 抄底、风险管理 |
| 8 | 💡 **Cathie Wood** | 颠覆性创新 | 营收增速>30%、研发投入、TAM | 科技、生物、新能源 |
| 9 | 🔬 **Philip Fisher** | 成长股/闲聊法 | 研发>10%、毛利率>50%、管理层 | 早期成长、细分龙头 |
| 10 | 🥇 **ARPS** | Crypto/黄金宏观 | BTC相关性、黄金避险、美元强弱 | 数字资产、避险 |
| 11 | 🤖 **Aschenbrenner** | AI地缘政治 | AI投入、算力需求、人才密度 | AI、算力、地缘政治 |
| 12 | ₿ **大宇 (BTCdayu)** | 币圈看准+重仓 | 情绪动量>估值、信息差>基本面 | Crypto、Meme、新叙事 |

> 📖 每位投资人都有完整的人格文档（`personas/*.md`），YAML自定义人格（`personas/custom/*.yaml`），和Python分析Agent（`scanner/personas/*.py`）。

---

## 🧬 人格进化追踪

投资人的判断不是静态的。系统追踪每位投资人的：

```
巴菲特进化时间线
1965 控股伯克希尔 → 1972 See‘s Candies(护城河) → 1988 可口可乐
→ 2008 金融危机逆向投资 → 2016 苹果(接受科技) → 2025 CRCL(接受加密)
```

| 投资人 | 关键事件 | 风格漂移 |
|--------|---------|---------|
| Buffett | 9个 (1965→2025) | 纯价值 → 价值+成长 → 接受加密 |
| 大宇 | 8个 (2021→2026) | 技术分析 → 信息差 → 三重仓位 |
| 更多 | 持续更新中... | |

分析时自动注入当前状态上下文，让判断更接近真实。

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
# → 访问 http://localhost:8000
```

### 命令行分析

```bash
# 分析单一标的（所有12位Agent）
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
📊 首页    - 市场总览
🤖 人格页  - 12位投资人对比
📈 分析页  - 单标的深度分析
🔄 辩论页  - Agent间模拟辩论
⚖️ 风险页  - Kelly仓位/Calmar比率
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
→ 返回12位Agent的共识分析结果
```

### 方案B：独立FastAPI + iframe嵌入

```bash
# 启动独立服务
python3 -m dashboard.app --port 8080 --cors

# 在Hermes Web UI中通过iframe嵌入
```

### 方案C：原生PR整合（进行中）

向 hermes-web-ui 提交PR，添加原生 "Investment Analysis" 页面：
- 人格选择器（12位投资大师）
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

```
buffett-oracle-analyzer/
│
├── scanner/                    # 分析引擎
│   ├── personas/               # 12位投资人人格Agent
│   │   ├── base.py             # Agent基类
│   │   ├── buffett.py          # 巴菲特
│   │   ├── graham.py           # 格雷厄姆
│   │   ├── lynch.py            # 彼得·林奇
│   │   ├── dalio.py            # 瑞·达利欧
│   │   ├── munger.py           # 查理·芒格
│   │   ├── soros.py            # 乔治·索罗斯
│   │   ├── marks.py            # 霍华德·马克斯
│   │   ├── cathie_wood.py      # 凯西·伍德
│   │   ├── fisher.py           # 菲利普·费雪
│   │   ├── arps.py             # ARPS Crypto/黄金
│   │   ├── aschenbrenner.py    # 阿申布伦纳(AI)
│   │   ├── dayu.py             # 大宇(币圈)
│   │   └── registry.py         # Agent注册中心
│   └── persona_loader.py       # YAML自定义人格加载
│
├── personas/                   # 投资人文档
│   ├── da-yu.md                # 大宇投资体系
│   ├── ray-dalio.md            # 达利欧宏观框架
│   ├── ... (12份文档)
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
- [ ] **v2.1**: Web UI增强（REST API + CORS + 截图）
- [ ] **v2.2**: Docker容器化 + 一键部署脚本
- [ ] **v2.3**: Hermes Web UI PR整合
- [ ] **v2.4**: 日频数据仓库 + 实时追踪仪表盘
- [ ] **v3.0**: 私有人格功能逐步迭代回公共版本

---

## 🤝 贡献指南

欢迎通过各种方式贡献：

1. **新投资人人格**：在 `personas/custom/` 下添加 YAML 文件
2. **算法优化**：改进 `scanner/personas/` 中的评分逻辑
3. **Web UI增强**：完善 `dashboard/` 前端界面
4. **文档**：完善 README 和人格文档
5. **PR到Hermes Web UI**：帮助项目与 hermes-web-ui 整合

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE)

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/BruceLanLan">BruceLanLan</a></sub>
  <br>
  <sub>Special thanks to <a href="https://dayu.xyz">大宇(BTCdayu)</a> for investment philosophy framework</sub>
</p>
