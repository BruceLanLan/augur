# Augur 未来方向头脑风暴（2026-07）

**日期**：2026-07-11
**性质**：发散清单，不是 roadmap。每条附"为什么现在具备条件 / 量级 / 风险"，供 owner 挑选后再写执行交接单。
**前提现状（采信，不重查）**：Phase A-F 全部完成，测试基线 2396 passed；PyPI 首发等用户 token（不可逆操作只能用户做）；R6 真实概率校准等 `~/.augur/learned_weights.json` 的 72 条 pending 预测积累 30+ 天真实数据（急不来）。本文档只谈这两个结构性阻塞**之外**还能做什么。

---

## 总览：四类共 14 个方向

| 类别 | 方向 | 量级 | 一句话判断 |
|------|------|------|-----------|
| B 数据/可信度 | B1 rolling_ic.json 生成器（复刻 R5 模式） | 半个~1 session | 引擎里 50/50 混合逻辑已在等这个文件，最便宜的可信度增量 |
| B 数据/可信度 | B2 因子级归因（factor-level IC） | 2-3 sessions | 回放管道和 ~70 因子都现成，缺的只是横截面统计脚本 |
| B 数据/可信度 | B3 regime 2018-2020 COVID 窗口重验证 | 1 session | roadmap 自己留的具体下一步，脚本改窗口就能跑 |
| B 数据/可信度 | B4 校准评估框架先行（Brier/reliability） | 1 session | 把 R6 的"等数据"变成"数据一到就能跑" |
| B 数据/可信度 | B5 13F CUSIP 覆盖扩展 | 1-2 sessions | 22-ticker 手工表是已文档化的限制，有免费扩展路径 |
| A 产品 | A1 组合层视角（portfolio-first） | 3-5 sessions | Markowitz 优化器+相关性矩阵+Kelly 都在，缺的是编排 |
| A 产品 | A2 新人格（做空/量化），用相关性矩阵做准入门槛 | 每个 1-2 sessions | R5 矩阵让"新人格是否真正多样"第一次可量化 |
| A 产品 | A3 财报季模式（EDGAR 事件驱动重评估） | 2-3 sessions | EDGAR 客户端+guidance 抽取+cron+bots 全部就位 |
| A 产品 | A4 委员会晨报（cron→bots 推送编排） | 1-2 sessions | 纯编排活，所有部件已存在 |
| A 产品 | A5 新资产类别：ETF 先行，加密观望，期权不建议 | ETF 2 sessions | ETF 与现有数据链兼容；加密会击穿大师因子体系 |
| C 分发 | C1 MCP 生态深耕（registry/打包/HTTP transport） | 1-2 sessions | 13 个 MCP tools 已成熟，是绕开 PyPI 阻塞的最大曝光面 |
| C 分发 | C2 零阻塞安装路径（git+/uvx/GitHub Release） | 半个 session | PyPI 等 token 期间的替代分发，改 README 就见效 |
| D 工程健康 | D1 `augur doctor` 环境自检命令 | 1-2 sessions | 今天的 LibreSSL 事故就是最好的需求证明 |
| D 工程健康 | D2 数据源健康可观测性 + 每周真实网络烟测 | 1-2 sessions | stooq 失效靠"顺手发现"，应该被监控发现 |

---

## B 类：数据/可信度（R6 之外）

可信度是已定战略主线的中段，R6 被时间阻塞不等于这条线只能停摆。以下五项都不依赖 pending 预测的积累。

### B1. rolling_ic.json 生成器 —— 复刻 R5 的成功模式

**发现**：`src/augur/consensus/rolling_ic.py` 的 `load_rolling_ic_weights()` 读取 `feedback/rolling_ic.json`，`engine.py:84-117` 在文件存在时会把 rolling-IC 权重与行业权重做 50/50 混合——但 repo 里只有 `feedback/rolling_ic.json.example`，**没有任何生成器脚本**。这与 R5 修复前的 `agent_correlation.json` 是同一个病：引擎里躺着一段永远静默跳过的加权逻辑。

**为什么现在能做**：R5 的 `scripts/generate_agent_correlation.py` 已经打通了完整管道——`fetch_ticker_replay_records`（EDGAR 时点基本面回放）+ `_signed_agent_scores`（带方向的打分约定），37 ticker、40,922 观测点。rolling IC 只是同一份数据换一个统计量（per-agent 滚动窗口 rank-IC 而不是 pairwise 相关），生成器可以大量复用 R5 脚本。

**量级**：半个到 1 个 session。

**风险**：与 regime weights 同一类——生成出来的 IC 权重**未必比行业权重好**。纪律要求：生成器落地 ≠ 默认启用，先用 OOS 窗口对比"50/50 混合 vs 纯行业权重"的横截面 IC，打平就学 Phase D 诚实地不启用（或把 example 文件和加载逻辑一起移除，承认这条路不通）。这条的价值一半在结论本身：要么多一层已验证的加权，要么少一段死代码。

### B2. 因子级归因 —— 从"哪个大师准"下探到"哪个因子在哪类股票上准"

**为什么现在能做**：三个部件都已存在。(1) ~70 个因子已通过 `metadata.factors` 结构化输出，前端 `factor-map.js` 有统一分类；(2) `BacktestRecord` 含 per-agent per-day 分数，`fetch_ticker_replay_records` 能以 EDGAR 时点纪律重放任意历史日；(3) `regime_weight_oos.py` 已示范了横截面 rank-IC 的正确算法（含"IC 轴线论证"那次方法论辩论的结论）。缺的只是把重放粒度从 agent 分数细化到 factor 值，再对每个因子算横截面 IC——一个新脚本，不动运行时代码。

**产出形态**：`scripts/factor_attribution.py` + 一份"因子 IC 排行/分行业热力图"报告（可进 dashboard 的 performance 页，也可只作为脚本产出）。它回答的问题是用户真正关心的："insider_buying_signal 这种新因子到底有没有用？EDGAR 花了四个 Phase 接进来的数据，哪些字段在赚 IC，哪些是噪音？"

**量级**：2-3 sessions（重放一次 37 ticker 全窗口约几十分钟，迭代成本主要在这里）。

**风险**：多重比较问题——70 个因子里总有几个碰巧 IC 显著，需要按行业/时间分半验证，避免"regime weights 第二季"。另外部分因子（sentiment 类）在历史重放中不可得（没有时点快照），归因只能覆盖可重放的因子子集，报告里要显式列出覆盖范围。

### B3. regime 权重 2018-2020 COVID 窗口重验证

**为什么现在能做**：这是 v10.6.0 CHANGELOG 和 roadmap Phase D 自己留下的、写得非常具体的未做项：FY2019 年报（大型加速申报公司通常 2020 年 1-2 月报完）在时点上**可能真的赶在 COVID 崩盘（2020-02~03）之前可用**，这是 2022 窗口验证失败（FY2022 年报 filed 日期集中在 2023-03，晚于熊市本身）之后唯一还站得住的假设。`scripts/regime_weight_oos.py` 现成，只需改窗口参数并确认 EDGAR companyfacts 对 2018-2020 的覆盖。

**量级**：1 session。

**风险**：两个都可能一试就破。(1) EDGAR companyfacts 对 2018 年的标签覆盖可能不如 2022+（XBRL 标签历史演变）；(2) 即使覆盖够，结论可能仍是"打平"——但那也是终局性结论：两个独立熊市窗口都打平，regime multipliers 这条路就可以永久关闭，删掉 `regime_weights.py` 里的空壳。做这件事的正确预期是"买一个终局结论"，不是"救活 regime 权重"。

### B4. 概率校准的评估框架先行

**为什么现在能做**：R6 阻塞的是**数据**，不是**代码**。`learning.py` 的预测记录已含 confidence 字段，resolve 后会有 outcome。可以现在就写好：reliability diagram 生成、Brier score / 校准误差计算、Platt scaling 与 isotonic regression 的拟合脚本（含"样本量不足 N 时拒绝拟合"的门），全部用合成数据测通。30 天后 pending 开始 resolve 时，直接跑真实数据出第一份校准报告，而不是那时才开始写代码。

**量级**：1 session。

**风险**：低。唯一要防的是过度设计——72 条预测即使全部 resolve 也只是 72 个样本点，isotonic regression 在这个量级上没有意义，第一版框架应该只做 reliability 分桶（3-5 桶）+ Brier，把 Platt/isotonic 留到样本量 200+。框架里把这个门槛写死，就是对"拍脑袋公式"（债 5）的制度性预防。

### B5. 13F CUSIP 覆盖扩展

**为什么现在能做**：v10.5.0 把"22-ticker 手工 CUSIP 表"作为文档化限制诚实地留下了。两条免费扩展路径：(1) 13F infoTable 自身含 `nameOfIssuer` + `cusip`，用已跟踪的 5 家机构的全部持仓反向积累 CUSIP→名称映射，再对名称做 ticker 匹配（Berkshire 一家的 13F 就覆盖数十个大盘股）；(2) OpenFIGI 免费 API（有 key 后限流宽松）支持 CUSIP→ticker 批量查询。`get_filing_index()` / 13F 解析器都是 10.5.0 现成的。

**量级**：1-2 sessions。

**风险**：名称匹配是脏活（"APPLE INC" vs "Apple Inc."、多股类如 GOOG/GOOGL 同发行人不同 CUSIP）；OpenFIGI 引入第三方依赖与 key 配置（但项目已有 FINNHUB/ALPHAVANTAGE 的可选 key 惯例可套用）。价值判断：`institutional_flow_signal` 目前只对 22 个大盘股有效，扩展后才谈得上普遍可用——但如果 B2 的因子归因发现这个因子本身 IC 不行，就不值得扩展。**建议 B2 先行，用归因结果决定 B5 做不做。**

---

## A 类：产品/功能

### A1. 组合层视角 —— 从"单票裁决"到"组合体检"

**为什么现在能做**：这是现有部件密度最高的一个方向。(1) `src/augur/optimizer.py` 已有完整的纯 Python Markowitz（最大 Sharpe、有效前沿、long-only 约束），515 行成熟代码但目前只是 dashboard 一个孤立页面；(2) `feedback/agent_correlation.json` 是真实数据；(3) Kelly 仓位建议已按单票输出；(4) `portfolio.py` 路由和 watchlist 持久化已存在。缺的是编排：把 watchlist 当作组合，18 大师对每只持仓的共识分数 + 持仓间相关性 + Kelly 汇总，输出"组合级诊断"——集中度警告、大师视角下的整体多空倾斜、"如果 Buffett 管理你的组合会先卖哪只"。

**产品含义**：这是从"分析工具"到"决策委员会"定位的实质跨越——委员会审的应该是你的整个组合，不是一次一票。也是与同类开源项目（多数停留在单票分析）的差异化点。

**量级**：3-5 sessions（第一版：CLI `augur portfolio-review` + dashboard 页；不做交易接口）。

**风险**：(1) 口径冲突——单票 Kelly 建议加总可能超过 100% 仓位，Kelly 与 Markowitz 两套仓位逻辑并存需要明确"谁是建议、谁是参考"，这是产品决策不是代码问题，动手前要先定；(2) 协方差估计需要每只持仓 1 年+ 日收益历史，数据源限流问题（cron 刚为此加了 inter-ticker delay）会在 10+ 持仓的组合上放大——依赖 D2 的缓存/健康层先行会更稳。

### A2. 新人格 —— 用相关性矩阵做"准入门槛"

**为什么现在能做**：机制上，`persona_loader` + YAML 自定义人格 + `augur_create_persona` MCP tool 早已支持新增；真正的新条件是 **R5 之后"人格多样性"第一次可量化**。R5 已发现现有 18 人中有 4 对相关性 >0.7（duan_yongping/zhang_lei 0.757 等）——价值/成长型人格已经拥挤。新人格的准入测试：在 37-ticker 回放数据上跑出它与现有 18 人的相关性，若与任何现有人格 >0.8 就承认它是冗余的，不合入。

**候选（按填补的空白排序）**：
- **做空/怀疑型**（Chanos 式）：现有 18 人没有系统性空头视角，committee 的"反方"目前靠 debate 机制模拟而非真实人格因子。EDGAR 数据恰好是做空人格的原料——高 debt_ratio、insider 集中卖出（insider 因子已有）、应收/营收背离（XBRL 概念已可取）。预计与现有矩阵相关性最低，最可能通过准入门槛。
- **量化因子型**（Asness 式）：直接消费 B2 的因子 IC 产出——"只信数据不信叙事"的人格，其打分就是已验证因子的加权。与 B2 有天然协同。
- **宏观债券/利率型**：填补 Dalio 之外的固收视角，但数据依赖（利率曲线）超出现有 MarketContext 字段，成本更高。

**量级**：每个人格 1-2 sessions（含准入验证）。

**风险**：主要是"人格通胀"——18 已经不少，每加一个都稀释共识里其他人的权重、增加维护面（i18n、soul、factor-map）。准入门槛（相关性 + 至少一个独有因子）就是防这个的。另外做空人格的因子若与 insider/13F 因子高度重叠，可能测出来它其实是"现有因子换了个皮"，那就诚实不加。

### A3. 财报季模式 —— EDGAR 事件驱动的重新评估

**为什么现在能做**：全部四个部件就位：(1) `EdgarClient.get_submissions()` 能枚举新 filing（10.5.0）；(2) `edgar_guidance.py` 能抽取 MD&A 展望（10.9.0，默认关）；(3) `cron.py` 有每日调度；(4) 四平台 bots 能推送。编排成：cron 检测 watchlist 内 ticker 的新 10-K/10-Q/8-K → 触发 guidance 抽取 + 共识重算 → 与上次共识 diff → 分数变动超阈值才推送"财报更新：大师们的看法变了"。这把 Augur 从"你想起来才查"变成"该看的时候它叫你"，是留存率意义上的功能。

**量级**：2-3 sessions。

**风险**：(1) guidance 的 LLM 抽取至今没做过真实付费调用验证（10.9.0 明确留给有 key 的用户）——这条线**依赖先补一次真实 LLM 端到端验证**，那是它的第 0 步；(2) 推送疲劳——财报季一天可能多只持仓同时出报，需要聚合而非逐条轰炸；(3) LLM 成本随 watchlist 规模线性增长，per-filing 永久缓存（已有）能兜住重复但兜不住首次。

### A4. 委员会晨报

**为什么现在能做**：`run_watchlist_analysis`（cron）已经每日跑 watchlist 共识，bots 已通四平台，缺的只是把结果编排成一份"今日委员会纪要"：分数变动 top 3、大师分歧最大的一只、pending 预测 resolve 进展（顺便让 R6 的数据积累对用户可见）。几乎纯模板工作。

**量级**：1-2 sessions。**风险**：低。最大的坑是时区/开闭市判断和"无变化日不发"的判断逻辑。这是投入产出比最高的"感知价值"项，适合当填充任务。

### A5. 新资产类别：ETF 先行，加密观望，期权不建议

- **ETF/指数**（建议做）：yfinance/finnhub 链路对 ETF 开箱即用，价格/RSI/SMA 等技术字段全兼容；EDGAR 基本面自然缺失但 `{"insufficient": True}` 降级路径就是为此设计的。需要的适配是：大师因子里基本面缺失时的打分行为审查（Graham 对一个没有 PE 的 SPY 说什么？）+ 可能给 ETF 单独的因子子集。量级 2 sessions。风险：18 人格对"一篮子"的叙事本来就弱，产品上更像"宏观委员会"而非选股委员会——可以接受但要想清楚呈现方式。
- **加密**（观望）：yfinance 有 BTC-USD 报价，但 EDGAR/13F/insider/财报因子**全部失效**，18 位大师中多数人格逻辑（Buffett 公开反对加密）会输出尴尬结果。做的话等于为加密重建一套因子体系 + 人格立场审查，量级 5+ sessions 且与现有可信度资产复用极少。判断：与"数据→可信度→发布"主线正交性太差，3-6 个月内不建议。
- **期权**（不建议）：免费数据源没有可靠期权链历史，时点纪律无法保证——这个项目的立身之本（可验证性）在期权上直接不成立。

---

## C 类：分发/生态（PyPI 之外）

### C1. MCP 生态深耕 —— 当前最大的免费曝光面

**为什么现在能做**：`mcp_server.py` 已有 13 个成熟 tools（analyze/consensus/debate/committee/workflow/workspace 全套），README 已标 "MCP Ready"。MCP 生态 2026 年的分发渠道（官方 registry、社区目录、Claude Desktop 的扩展打包格式）不需要 PyPI——`uvx --from git+...` 或本地安装即可注册。具体可做：(1) 提交到 MCP 官方 registry / 主流社区目录；(2) 打包 Desktop Extension 让 Claude Desktop 用户一键安装；(3) 若当前只有 stdio transport，补 streamable HTTP，使远程/多客户端场景可用。

**量级**：1-2 sessions（主要是打包与目录提交的杂活）。

**风险**：目录审核周期不可控；"18 个投资人格"在 agent 工具目录里是稀缺题材，但投资类工具可能面临更严的免责声明要求（README 已有免责声明，需要确认覆盖英文与工具描述内）。判断依据：这是唯一**不被 PyPI token 阻塞、又直接触达真实用户**的分发动作，值得排在 C 类第一。

### C2. 零阻塞安装路径

**为什么现在能做**：Phase F 已验证 `python -m build` + 干净 venv 真实安装全通。在 PyPI token 到位前：README 顶部给 `pip install git+https://github.com/.../augur.git` 与 `uvx` 用法；GitHub Release 挂 wheel（`publish.yml` 已存在，可加 release 触发）。**量级**：半个 session。**风险**：几乎没有。这不替代 PyPI，只是消灭"等 token 期间没人装得上"的空窗。

### C3. Web 只读 demo（低优先级，列出供参考）

dashboard 是标准 FastAPI 应用，理论上可部署一个公开只读 demo（R2 的显式 demo 模式标注是现成的诚实机制）。但服务器端数据源限流、运维成本、投资内容合规都是新麻烦，且与"个人工具"定位有张力。判断：等 C1/C2 见效后再议，3-6 个月内不主动做。

---

## D 类：工程健康（R7 之外）

### D1. `augur doctor` —— 环境自检命令

**为什么现在能做**：今天的事故是完美需求证明——`.venv` 用了 CommandLineTools python3.9（LibreSSL 2.8.3），curl_cffi SSLError 导致所有真实 yfinance 调用静默受阻，而项目对此毫无自检能力。原料齐全：`optional_deps.OPTIONAL_DEPS_REGISTRY`（依赖注册表）、datasources chain（每个 provider 可单独 ping）、API key 惯例（FINNHUB/ALPHAVANTAGE/OPENAI）、`~/.augur/learned_weights.json`（pending/resolved 状态）。`augur doctor` 输出：Python/SSL 版本与已知坏组合警告、各数据源连通性实测、key 配置状态、EDGAR contact email 是否设置、学习引擎数据积累进度。

**顺手项**：`requires-python = ">=3.8"` 这个下限值得重新审视——3.8 已 EOL 两年+，而正是过低的下限让 venv 落在系统 3.9 上没有任何警告。提高到 >=3.10（或至少在 doctor 里对 <3.10 + LibreSSL 的组合亮红灯）是一行改动加一个决定。

**量级**：1-2 sessions。**风险**：低。唯一的设计张力是"连通性实测"会真实打外网，需要 `--offline` 旗标。这也是给未来所有 issue 报告者的第一句回复："先贴 `augur doctor` 输出"——对开源发布后的维护成本是杠杆性投入。

### D2. 数据源健康可观测性 + 定期真实烟测

**为什么现在能做**：stooq 失效是这周"顺手发现"并只能补一条文档记录（commit 24c8609）——说明 fallback chain 的命中/失败**没有任何统计**。轻量方案：datasources chain 每次 fallback 记一条本地计数（`~/.augur/provider_stats.json`），dashboard misc 页或 `augur doctor` 展示"过去 7 天 yfinance 成功率 / 降级到 finnhub 次数"。配套：`.github/workflows/` 已有 tests.yml，加一个每周 scheduled workflow 只跑真实网络冒烟（EDGAR CIK lookup + companyfacts 各一发；yfinance 一发但**允许失败仅告警**，因为 CI IP 大概率被限流）——让 stooq 式的静默失效变成一封 GitHub 通知。

**量级**：1-2 sessions。**风险**：CI 里 yfinance 的误报率可能高到告警疲劳，所以设计成"EDGAR 失败才红、yfinance 失败只黄"；本地统计要注意不引入任何网络回传（纯本地文件，符合个人工具的隐私预期）。

### D3. 性能/限流韧性（列出但不展开）

cron 刚加 inter-ticker delay（9e9dc33）说明 watchlist 扫描是串行 + 受限流驱动的。市场数据的进程内 TTL 缓存（同一 ticker 在 analyze→consensus→committee 链条里可能被重复拉取）值得排查一次。量级 1 session 的调查先行，有实测重复拉取证据再做缓存。风险：缓存引入的时点污染正是这个项目最忌讳的 bug 类别，做之前必须想清楚 TTL 与回测路径的隔离。

---

## 挑选建议（不是决定）

**协同关系**：B2（因子归因）是多个方向的上游——它的结论决定 B5（13F 扩展值不值）、喂 A2 的量化人格、也给 B1（rolling IC）提供方法论复用。若只挑一个 B 类项，挑 B2。

**互补组合**：一条务实的 3 个月组合是 **C2 + C1（把能装、能被发现先解决）→ D1 + D2（发布前把自检和监控立起来，降低开源后维护成本）→ B2（可信度纵深）→ A1 或 A3（产品跨越）**。A4/B3/B4 是任意间隙都能塞的 1-session 填充项。

**明确不建议在 3-6 个月内做的**：加密（A5，因子体系不复用）、期权（A5，时点纪律不成立）、Web 公开 demo（C3，运维与合规成本对个人工具不划算）。

**纪律提醒（沿用本项目自己的先例）**：B1/B3/A2 三项都内置了"验证失败就诚实移除/不合入"的出口——这是 regime weights（v10.6.0 验证打平后清空）和 X sentiment（v10.7.0 mock 退出加权）留下的传统，挑选时请把"负结论也是产出"计入预期价值。
