# Augur 项目全面 Review 与发展规划

**日期**：2026-07-06
**评审模型**：Fable 5（规划）→ 交接给 Sonnet 5（开发）
**当前版本**：v10.2.0，测试基线 2219 passed
**已定战略主线（不重开）**：数据 → 可信度 → 发布

---

## 一、Review：项目现状评估

### 1.1 真实优势（有证据支撑的部分）

- **测试文化是真的**。2219 个测试不是摆设：包含行为测试（consensus 数学、时点纪律、API 契约）、回归防护（打包布局、i18n 覆盖）、真实 bug 的回归测试（NaN 老列、空抓取缓存污染、factor-map 值碰撞去重）。每次改动跑全量的纪律已经在 CHANGELOG 里形成惯例。
- **时点纪律经过实战检验**。P2-4（v10.16.9）从"发现回测喂常数零"到"修 yfinance NaN 列 bug"再到"横截面 IC 轴线论证"，整个过程的方法论是严肃的。EDGAR spec 沿用这套纪律。
- **模块化已完成大半**。dashboard 从 4338 行 God file 拆成 17 个路由模块（v10.1.0）；consensus 逻辑独立成 `src/augur/consensus/` 包。
- **打包缺陷刚修复**（v10.2.0）：`pip install augur-agents` 后 `augur serve` 真正可用，且有 9 个回归测试防止复发。
- **18 personas 的因子体系已结构化**：约 70 个因子通过 `metadata.factors` 输出，前端有统一的分类映射（`factor-map.js`），新增因子（如 EDGAR 的 insider_buying_signal）有现成的接入路径。
- **文档诚实文化**：`AGENT_PEER_REVIEW_SYNTHESIS.md` 的 gate 语言（"结果是打平，不是验证通过"）在开源项目里少见，值得保持。

### 1.2 架构债清单（按严重性排序，每条带证据坐标）

#### 债 1（致命）：MetaModel stub 以 50% 权重稀释整个共识

- **证据**：`src/augur/consensus/meta_model.py` 全文 24 行，docstring 自称 "Lightweight stub — blends toward median agent score when loaded"，`predict()` 只是取 agent 分数的中位数。`src/augur/consensus/engine.py:218-231` 中 `MetaModel.load()` 永远返回激活实例，默认 `meta_model_weight = 0.5`，即 `total_score = 0.5 * 精心加权的分数 + 0.5 * 中位数`。engine.py 的注释原文承认："the blend weight below is the *only* way to dial down how much the cross-agent median washes out the industry/regime-tuned weighted score."
- **后果**：行业加权、regime 加权、learned 权重、diversity penalty、sector boost——所有这些逻辑的效果被砍半。P2-4 花大力气验证 regime 权重"打平"，而验证时这个 stub 正在稀释被验证对象本身。
- **判断**：一个从未被验证有增益的 stub 不应该默认开启（与 P2-4 "没验证的东西不下结论"是同一条纪律）。

#### 债 2（致命）：Dashboard 回测页跑的是合成数据

- **证据**：`src/dashboard/routes/backtest.py:33` 的 `/api/backtest/run` 调用 `generate_sample_data(ticker, days)`——hash 种子的确定性假数据；`src/augur/cli.py:681` 的 CLI backtest 命令同样。真实历史数据路径 `Backtester.run_live_backtest`（`src/augur/backtest.py:450`，含时点基本面）存在但没有暴露给 dashboard 或 CLI 默认路径。
- **后果**：用户在 `/backtest` 页面看到的 IC、命中率、"回测结果"全部来自合成数据；`/performance` 的 IC 排行榜数据同源。这是可信度主线上最直接的信任损伤——系统展示的"历史验证"不是历史。
- **判断**：合成数据当 demo 有其价值（无网络可用、秒出结果），但必须显式标注，且真实路径应为默认。

#### 债 3（严重）：LearningEngine 学习闭环实际不闭合

- **证据**：outcome resolve 的唯一触发点是 `engine.py:377-380`（`_check_and_record_outcomes` 在每次 consensus 计算时检查该 ticker 的旧预测）。这要求"30 天后有人恰好再次分析同一 ticker"。没有定时兜底任务。实际后果已经发生：用户机器上 `~/.augur/learned_weights.json` 不存在（2026-07-02 验证），系统运行了几十个版本，学习引擎没有积累任何 resolved outcome。
- **后果**：v8 起承诺的"agent 越用越准"的学习机制、performance 页新做的 live win-rate 展示、未来可信度层的校准数据，全部没有数据来源。
- **判断**：需要一个定时任务扫描所有 pending predictions，到期的拉真实价格 resolve——`augur.cron` 基础设施已存在，缺的只是接上。

#### 债 4（中）：X sentiment 权重里混着 hash mock

- **证据**：`src/augur/sentiment.py:11`——"X (Twitter) 20% — hash mock (X API free tier too restrictive for real use)"。Reddit/StockTwits 是真实 API（带 mock fallback），但 X 恒为 hash 假数据，占 20% 权重，且 `get_sentiment_factor` 的结果直接进共识分数（`engine.py:172-178`，±0.5 分）。
- **后果**：每个共识分数里有一小部分由确定性假数据驱动。影响量级小（±0.5 × 20%），但性质与债 2 相同。

#### 债 5（中）：probability_calibrator 是拍脑袋公式，不是校准

- **证据**：`src/augur/consensus/probability_calibrator.py` 全文 12 行，`calibrated = confidence * (0.85 + 0.15 * extremity)`——一个与历史准确率无关的线性调整。真校准（Platt scaling / isotonic regression）需要历史"预测置信度 vs 实际命中"数据，而这些数据正是债 3 里缺失的。
- **判断**：依赖债 3 修复后的数据积累，属于可信度层的后续工作，不是当前阻断。

#### 债 6（中）：agent_correlation.json 从未真实生效

- **证据**：`engine.py:63-69` 加载 `agent_correlation.json` 做 diversity penalty，但 repo 里只有 `feedback/agent_correlation.json.example`，没有生成器脚本。除非用户手动创建该文件，这段逻辑静默跳过。
- **判断**：回测记录（BacktestRecord 含 per-agent per-day 分数）足以计算真实的 agent 间相关性，缺一个生成脚本。

#### 债 7（低，工程健康）：cli.py 1457 行 God file

- **证据**：`wc -l` 排名第一。dashboard 同样的问题已在 v10.1.0 拆完（17 个模块），CLI 还是单文件。
- **判断**：不影响正确性，但每次加 CLI 命令都在加剧。优先级低于以上所有。

### 1.3 Review 结论

项目的工程质量（测试、模块化、文档）高于典型个人项目，但**可信度链条上有三个正在流血的伤口（债 1/2/3）**：共识分数被 stub 稀释一半、UI 展示的回测是假数据、学习引擎从未学到东西。这三项不修，EDGAR 数据深化的产出会继续被同样的管道失真——先修管道，再灌新数据。

---

## 二、重构方案（分级 + 排序依据）

排序依据：债 1/2/3 是已批准的 EDGAR 主线的**前置依赖**（理由见 1.3），必须先做；债 4/6 是低成本高诚实收益的顺手项；债 5 依赖数据积累只能延后；债 7 与主线无关放最后。

| 编号 | 内容 | 级别 | 依赖 | 状态 |
|------|------|------|------|------|
| R1 | MetaModel 默认权重归零 | P0 | 无 | 已完成（v10.3.0） |
| R2 | Dashboard/CLI 回测切真实数据路径 | P0 | 无 | 已完成（v10.3.0） |
| R3 | LearningEngine 定时 resolve 兜底 | P0 | 无 | 已完成（v10.3.0） |
| R4 | X sentiment mock 退出加权 | P1 | 无 | 已完成（v10.7.0） |
| R5 | agent_correlation 生成器脚本 | P1 | 无 | 已完成（v10.7.0，真实数据：37 ticker、40922 观测点） |
| R6 | 真实概率校准 | P2 | R3 积累数据后 | 结构性阻塞——`~/.augur/learned_weights.json` 仍全 pending、0 resolved，等 30+ 天真实数据 |
| R7 | cli.py 拆分 | P2 | 无 | 已完成（v10.8.0，1476 行拆成 9 个 cli_commands 模块 + 103 行注册壳） |

R1/R2/R3 合计预估 2-3 个开发 session；R4/R5 各半个 session。

---

## 三、发展路线图

已定主线"数据 → 可信度 → 发布"不变，插入 Phase A 作为前置：

```
Phase A  P0 重构（R1+R2+R3，本文档 §四给出交接单）        ← 下一步
Phase B  EDGAR 阶段1：XBRL 财报基础设施                    ← spec 已批准
Phase C  EDGAR 阶段2+3：Form 4 内部人 + 13F 机构持仓
Phase D  可信度层深化：
         - 用修好的 LearningEngine + EDGAR 长历史重跑校准 —— 结构性时间阻塞：
           R3 的持久化修复本 session 才生效，pending 预测需真实等 30+ 天才能
           resolve，`~/.augur/learned_weights.json` 目前 18 条全 pending、
           0 条 resolved，现在做不了任何有意义的校准。
         - R6 真实概率校准 —— 同上，阻塞原因相同。
         - regime 权重重验证 —— **已在 B1（v10.4.0, commit f3df8ad）完成**：
           `scripts/regime_weight_oos.py` 用 EDGAR 真实 filing date 跑了
           37 支跨行业 ticker、2022-01～2026-06 全窗口截面 IC，诚实结论是
           "_REGIME_ADJUSTMENTS 无明显 OOS 提升"（各 regime 桶 delta 小且
           方向不一）。**原路线图设想的"2010s 数据解锁 2022 熊市"未成立**：
           EDGAR 数据深度虽够，但 FY2022 年报的真实 filed 日期集中在
           2023 年 3 月前后（12 月财年结束的大盘股 60~90 天申报窗），
           已晚于 2022 熊市（大致 1～10 月）本身——这是真实 filing 时点
           决定的，不是数据覆盖问题。BEAR_HIGH_VOL 桶实际覆盖到的是
           2024-08（日元套息平仓）与 2025-04（关税冲击）两段插曲，共 9
           天，仍然稀薄。是否保留/调整/移除 regime multipliers 留给用户
           决定（详见 CHANGELOG 10.4.0）。如果想进一步验证，把窗口前移到
           2018～2020（覆盖 2020 COVID 崩盘——12 月财年 FY2019 年报通常
           1～2 月就报完，时点上可能真的赶在崩盘前可用）是一个具体可执行
           的下一步，尚未做。
Phase E  EDGAR 阶段4：LLM 指引抽取（默认关闭，可选）—— **已完成（v10.9.0）**：
         `edgar_guidance.py` + `augur guidance TICKER`，从最新 10-K/10-Q
         的 MD&A 章节抽取管理层展望情绪/前瞻指引数字/风险变化，默认关闭
         （`AUGUR_EDGAR_GUIDANCE_EXTRACTION=1` 显式开启），不接入自动
         analyze()/consensus 管线（按 spec 要求仅按需调用）。真实验证覆盖
         到 EDGAR 抓取+MD&A 边界定位（真实 AAPL 10-Q，21905 字符，边界
         定位正确排除了 Part II 同名 Item 2/3）；LLM 抽取本身受限于本环境
         无 `OPENAI_API_KEY`，未做真实付费调用验证，单测里全部 mock——
         真实 LLM 端到端验证是留给有 API key 的用户的后续步骤。
Phase F  发布：PyPI 正式发布 + README/对外内容 + R4/R5/R7 收尾 —— **README/
         对外内容已完成（commit 86bd46d）**：README.md/README_EN.md 版本号
         徽章（v10.0.0→v10.9.0）、测试数徽章（2136→2388）、补全缺失的 CLI
         命令（report/committee/chat/fetch/sentiment/guidance/ic-report/
         watchlist-*/cron-*/inject-soul/update），RELEASE_NOTES.md 中英文
         都新增了本轮可信度修复的用户向说明。**只改了 augur-next 本仓库，
         没碰公开 augur 仓库**（按用户指示）。R4/R5/R7 早已完成（见 §二表格）。
         **PyPI 正式发布未做**：真实查了 PyPI，`augur-agents` 从未发布过
         （404），首次发布不可逆（删不掉、只能 yank）。已做的是本地验证——
         `python -m build` + `twine check` 全过，真实 wheel 装进干净 venv
         验证 `augur skills`/`augur serve` 的 dashboard import/`augur analyze`
         全部工作正常（这也顺带把 R7 的 cli_commands/ 路径深度改动在真实
         安装场景下验证了一遍）。真正 `twine upload` 留给用户提供 token
         时再做。
```

EDGAR 四阶段的完整设计见 `docs/superpowers/specs/2026-07-03-edgar-fundamentals-design.md`（已批准，不在本文档重复）。

**Phase C 之后的交接单等 Phase A/B 落地后再写**——提前写细节只会过期。本文档只给 Phase A 三张 + Phase B 一张。

---

## 四、开发交接单（给 Sonnet 5，T6 格式）

### 通用约定（每张单都适用，不再重复）

- **测试基线**：开工前 `python3 -m pytest -q --tb=no 2>&1 | tail -3` 确认 2219 passed（预存基线，若有出入先报告再动手）。完工后同样跑，只增不减。
- **commit**：完成一张单 commit 一次，英文 message，结尾 `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`。不 push（push 需用户单独授权，且只推 origin/augur-next，绝不碰 augur remote）。
- **语言**：代码/注释/commit 英文，文档中文。
- **版本号**：Phase A 三张单全部完成后统一升一次 minor（三处同步：`pyproject.toml`、`src/augur/__init__.py`、`hermes-agents/*.yaml` + skills manifests 用 `scripts/generate_skills.py` 再生成），并补 CHANGELOG。
- **没验证的不说完成**：每张单的验证点必须真实跑过，输出贴进完成报告。

---

### 交接单 R1：MetaModel 默认权重归零

**目标**：共识分数不再被未验证的中位数 stub 稀释；`meta_model_weight` 默认值从 0.5 改为 0.0，接口保留，配置可显式调回。

**背景事实**：
- `src/augur/consensus/meta_model.py`：`MetaModel.load()` 永远返回激活实例，`predict()` 取中位数。
- `src/augur/consensus/engine.py` 约 218-231 行：`meta_weight = get_config().get("consensus", {}).get("meta_model_weight", 0.5)`，随后 `total_score = (1 - meta_weight) * total_score + meta_weight * mm_score`。
- 该混合从未被验证有增益；它稀释所有上游加权逻辑（行业/regime/learned/diversity）。
- 现有测试里可能有依赖 0.5 默认值的断言（分数期望值）。

**约束**：
- 不删除 MetaModel 类和混合代码路径——将来可能接真实 meta 模型，接口保留。
- 配置显式设置 `consensus.meta_model_weight: 0.5` 时行为必须与现在完全一致（向后兼容）。

**步骤**（按风险排序）：
1. 全局 grep `meta_model_weight` 和 `MetaModel`，列出所有引用点（含测试）→ 验证点：确认除 engine.py 与 meta_model.py 外没有其他运行时消费方 → 若发现其他消费方：停下报告。
2. 改 engine.py 默认值 `0.5 → 0.0`，并更新该处注释（说明为什么默认 0：stub 未验证，接口保留待真模型）→ 验证点：`grep -n "meta_model_weight" src/augur/consensus/engine.py` 显示新默认值。
3. 跑全量测试 → 验证点：若有测试因分数期望变化而挂，逐个检查——期望值写死了 0.5 混合结果的，更新期望并在 commit message 说明；若挂的是行为断言（如"分数必须在 0-10"），说明改动引入了真 bug，回退排查。
4. 新增测试 `tests/test_meta_model_weight.py`：(a) 默认配置下 mm_score 不影响 total_score；(b) 显式配置 0.5 时行为与旧版一致（构造 agent 分数使加权分与中位数可区分，断言混合结果）。→ 验证点：新测试通过，全量通过。

**范围边界**：不实现真实 meta 模型；不动 MetaModel.predict 的中位数逻辑；不改配置系统本身。

**完成定义**：全量测试通过（数量 ≥ 2219 + 新增）；完成报告含步骤 3 中受影响测试的清单与处理方式。

---

### 交接单 R2：回测切真实数据路径，合成数据降级为显式 demo

**目标**：`/api/backtest/run` 与 `augur backtest` CLI 默认使用真实历史数据（`run_live_backtest`），合成数据仅在显式请求 `mode=demo` 时使用且 UI 明确标注。

**背景事实**：
- 合成路径：`src/dashboard/routes/backtest.py` 约 33 行 `generate_sample_data(ticker, days)`；`src/augur/cli.py:681` 同样。
- 真实路径：`Backtester.run_live_backtest(ticker, days)`（`src/augur/backtest.py:450`），拉真实价格 + 时点基本面（当前用 pit_fundamentals，Phase B 会换成 EDGAR，本单不管这一层）。
- 真实路径特性：需要网络；对 60 天回测每 ticker 会有一次年报拉取 + 价格历史拉取，耗时秒级到十秒级；网络失败时会返回空/部分结果。
- `/backtest` 页面模板：`src/dashboard/templates/backtest.html`；leaderboard 数据持久化在 `Backtester` 的存储里（`get_leaderboard()` 读取），历史合成数据产生的记录会污染排行榜。

**约束**：
- API 向后兼容：`/api/backtest/run` 现有参数不删，新增 `mode` 参数（`live`|`demo`），默认 `live`。
- 网络失败时不允许静默降级到合成数据——失败就报失败（忠实报告原则），响应里说明原因。
- CLI 同步：`augur backtest AAPL` 默认 live，`--demo` flag 保留合成路径。

**步骤**：
1. 读 `run_live_backtest` 完整实现与返回结构，确认与 `run_backtest`（合成路径消费的）返回结构的差异 → 验证点：列出两者字段差异清单；若结构不兼容到 UI 需要大改：停下报告方案再动。
2. 改 `/api/backtest/run`：`mode` 参数 + live 默认 + 网络失败返回明确错误（HTTP 200 + status:error + 原因，或 502，选与项目现有错误约定一致的方式——参考 scanner 的错误格式 `routes/analysis.py` 约 90-103 行）→ 验证点：本地起服务，`curl "/api/backtest/run?ticker=AAPL&days=30"` 返回真实数据（response 里 data_source 字段 = "live"）；`curl "...&mode=demo"` 返回合成数据且标注 demo。
3. 改 CLI 同款 → 验证点：`augur backtest AAPL --days 30` 实跑一次输出真实结果；`--demo` 输出带 demo 标注。
4. `backtest.html` UI：demo 模式结果显示明确的"演示数据"徽标；live 失败时显示错误信息而非空白 → 验证点：浏览器实测两种模式（可用 playwright 或手动 curl 页面确认元素存在）。
5. leaderboard 污染处理：`get_leaderboard()` 的存量记录里合成数据与真实数据无法区分——本单采取最小方案：新写入的记录带 `data_source` 字段，leaderboard API 响应透传该字段，UI 对无标注的历史记录显示"来源未知（旧数据）"。→ 验证点：新跑一次 live 回测后 leaderboard 响应含 data_source。
6. 测试：mode 参数路由逻辑（mock `run_live_backtest`）、网络失败的错误响应、demo 模式标注字段 → 验证点：新测试 + 全量通过。

**范围边界**：不动 `run_live_backtest` 内部实现（数据质量问题属 Phase B）；不清洗历史 leaderboard 存量数据；不做回测结果缓存。

**完成定义**：全量测试通过；完成报告含步骤 2/3 的真实 curl/CLI 输出片段（证明 live 路径真实跑通）。

---

### 交接单 R3：LearningEngine 定时 resolve 兜底

**目标**：pending predictions 不再依赖"用户恰好重复分析"才 resolve；cron 每日扫描所有到期预测，拉真实价格计算 outcome，学习闭环真正闭合。

**背景事实**：
- 现状唯一触发点：`src/augur/consensus/engine.py:377-380`，consensus 计算时调 `_check_and_record_outcomes(le, ticker)`（定义在 `src/augur/registry.py`）——只 resolve 当前 ticker。
- `LearningEngine.record_outcome(ticker, actual_return, lookback_days, min_age_days)`（`src/augur/learning.py:157`）已支持按 ticker resolve，30 天最小年龄逻辑已实现。
- pending 清单可从 `le._predictions` 里 `outcome is None` 的条目取 ticker 集合（`pending_count` property 已存在，`learning.py:325` 附近）。
- cron 基础设施：`src/augur/cron.py` 有 `run_watchlist_analysis`，调度配置在 `~/.augur/watchlist.yaml` 的 `schedule` 键；dashboard 的 cron 路由在 `src/dashboard/routes/notifications_cron.py`。
- 价格获取：`augur.data.fetch_history(ticker, period=...)` 可拉历史收盘价，30 天实际回报 = (当前价 - 预测时价格) / 预测时价格——注意：**预测记录里没存预测时价格**（`record_prediction` 只存 signal/score/confidence/timestamp），需要用 fetch_history 按 timestamp 反查当时价格。
- `LearningEngine._predictions` 只保留最后 100 条（`_save_weights` 里 `[-100:]`）——高频使用下预测会在 resolve 前被挤出。这是本单要一并处理的隐藏问题。

**约束**：
- resolve 失败（拉不到价格）的预测保持 pending，下次重试，不标记为失败。
- `_predictions` 保留策略改动不能让文件无限膨胀——resolved 条目可以修剪，pending 条目不可以。

**步骤**（按风险排序，最不确定的在前）：
1. 先解决"预测时价格缺失"：`record_prediction` 新增可选参数 `price`，consensus 调用处（engine.py:382-388）传入 `context.price`——注意 `compute()` 的 `context` 参数可为 None（签名 `Optional[MarketContext]`），None 或 price≤0 时传 0 表示未知，resolve 时按"缺失"路径处理；resolve 时优先用存储的 price，缺失（旧记录或 price=0）则用 fetch_history 按日期反查 → 验证点：新预测记录含 price 字段；单测覆盖存储 price / 反查 / context 为 None 三条路径。
2. 改 `_predictions` 保留策略：pending 的永不修剪，resolved 的保留最后 100 条 → 验证点：单测——构造 150 条 pending + 50 条 resolved，save/load 后 pending 全在。
3. 新增 `LearningEngine.resolve_pending(fetch_price_fn) -> dict`：扫描 pending 中 age ≥ 30 天的，按 ticker 分组拉价格算实际回报，调 record_outcome；返回 `{resolved: n, failed: n, still_pending: n}` → 验证点：单测 mock fetch_price_fn，验证到期的被 resolve、未到期的跳过、拉价失败的保持 pending。
4. 接入 cron：`run_watchlist_analysis` 末尾（或独立函数 `run_outcome_resolution`，由同一调度触发）调 resolve_pending → 验证点：单测 mock 后确认 cron 路径触发 resolve；`augur cron run-now` 手动实跑一次不报错。
5. dashboard 可见性：`/api/backtest/leaderboard` 已有 `pending_count`，本单在响应里加 `last_resolution`（时间戳 + resolved 计数，存 `~/.augur/learned_weights.json` 的元数据里）→ 验证点：resolve 跑过后 API 响应含该字段。
6. 全量测试 → 验证点：≥ 2219 + 新增全部通过。

**范围边界**：不改 30 天窗口和 ±2% 阈值这些评估参数；不做 R6 的概率校准；不动 performance 页 UI（已有 pending 提示够用）。

**完成定义**：全量通过；完成报告含一次真实 `resolve_pending` 运行输出（哪怕 resolved=0，证明管道通了）；说明旧格式预测记录（无 price）的兼容处理方式。

---

### 交接单 B1：EDGAR 阶段 1 —— XBRL 财报基础设施

**目标**：`EdgarClient` + `fetch_edgar_fundamentals(ticker, as_of_date, price)` 落地，实时分析与回测的基本面数据源切换为"EDGAR 优先、yfinance 降级"，`pit_fundamentals.py` 废弃删除。

**背景事实**：完整设计见 `docs/superpowers/specs/2026-07-03-edgar-fundamentals-design.md`（已批准）。执行前先通读该 spec 的"整体架构"与"阶段 1"两节。关键补充事实：
- 替换点 1（回测）：`src/augur/backtest.py` 两处 `fetch_pit_fundamentals` 调用（约 462/518 与 717/741 行附近）。
- 替换点 2（实时）：`augur.data.fetch_market_context` 是实时字段的产地（`src/augur/data.py`），EDGAR 优先逻辑加在这里。
- 现有测试 `tests/test_pit_fundamentals.py`（16 个）定义了时点纪律的行为契约——迁移为 `tests/test_edgar_fundamentals.py` 时保留全部行为断言（look-ahead 守卫、insufficient 标记、YoY 只用 as-of 可得的两期），替换数据构造方式为合成 XBRL JSON。
- SEC 限制：10 req/sec、必须带 `User-Agent: <项目名> <邮箱>`，邮箱走环境变量 `AUGUR_EDGAR_CONTACT_EMAIL`。
- EDGAR companyfacts API：`https://data.sec.gov/api/xbrl/companyfacts/CIK{10位补零}.json`；CIK 映射表：`https://www.sec.gov/files/company_tickers.json`。
- XBRL 概念标签有历史演变（如 Revenue 有多个变体标签），取数时按 spec 列的概念清单做多标签回退。

**约束**：
- 单测全部离线（合成 JSON），联网验证放手动步骤。
- 降级链必须完整：非美股/CIK 失败/网络失败 → yfinance → 全失败才 insufficient。
- `never raises` 原则贯穿。

**步骤**：
1. `EdgarClient`（CIK 映射 + 限流 + 缓存 `~/.augur/edgar_cache/`）→ 验证点：单测（mock HTTP）覆盖限流器、缓存命中、CIK 未找到；手动 `python3 -c "...lookup AAPL"` 实跑返回 CIK 320193。
2. `fetch_edgar_fundamentals`（companyfacts 解析 + 多标签回退 + 时点选择）→ 验证点：迁移的 16 个行为测试全绿；手动实跑 `("NVDA", "2015-06-01")` 返回非零基本面（yfinance 方案做不到的年份）。
3. 接入 `fetch_market_context`（EDGAR 优先、yfinance 降级）→ 验证点：手动实跑 AAPL 确认 pe/roe 来源标注为 edgar；实跑一个港股 ticker 确认降级到 yfinance 不报错。
4. 替换 backtest.py 两处调用，删除 `pit_fundamentals.py` 与旧测试文件 → 验证点：全量测试通过；`grep -rn "pit_fundamentals" src/ tests/` 为空。
5. 手动端到端：`scripts/regime_weight_oos.py` 用 3 个 ticker、2015-2018 窗口短跑一次，确认 EDGAR 数据流入横截面 IC 管道（这是 Phase D 重验证的前哨确认，不求结论只求管道通）→ 验证点：脚本输出显示 2015-2018 有非零覆盖天数。
6. CHANGELOG + 版本号（若 Phase A 已升过版本，此处再升一次 minor）。

**范围边界**：spec 的阶段 2/3/4 全部不做；不动 persona 打分逻辑；不重跑完整 regime 验证（那是 Phase D）。

**完成定义**：全量通过；完成报告含步骤 2/3/5 的真实运行输出。

---

## 五、执行顺序与里程碑

```
R1 → R2 → R3 →（版本号 + CHANGELOG，一次 minor）→ B1 →（版本号 + CHANGELOG）
```

- R1 最先：改动最小（一个默认值 + 测试），且它影响所有后续分数的语义——越早改，后面的验证越干净。
- R2/R3 无相互依赖，顺序可换，但都在 B1 之前（B1 的数据会流经它们修好的管道）。
- 每张单完成后 commit；用户授权后 push origin。
- B1 完成即 Phase B 结束，回本文档 §三 看 Phase C，届时再写新交接单。

## 六、给执行模型的最后提醒

本文档的交接单已按 T6 格式写成自包含形式，但代码库是活的——若单里引用的行号/结构与实际不符（可能被中间提交移动过），以 grep 实际定位为准，diff 大到改变方案时停下报告，不要硬套。每张单的"完成定义"是硬门：没有真实运行输出佐证的"完成"不算完成。
