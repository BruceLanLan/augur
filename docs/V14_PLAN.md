# Augur v14.0.0 规划交接单

日期：2026-11-26 ｜ 基线：main `ccce067`（v13.0.0，全量测试 3615 passed / 1 skipped）｜ 执行窗口：一个工作日，多条工作流并行

行号已对照当前代码核对；标"未核实"的来自调研摘要，执行时先确认。

## 1. 目标与主打功能

**主打：ETF 原生分析**——`augur fetch/consensus/report SPY` 把 ETF 当基金看（规模、费率、溢价折价、持仓集中度），不再按公司打分。

为什么选它：

- 现在的输出是错的，不只是缺功能：SPY 市值 $0.0B、被判"小市值""毛利率过低"，18 位大师照常投票，结果还写进 learning 样本。
- 直接回应 issue #5，是唯一来自外部用户的功能请求。
- 数据免费可得（yfinance 的 `navPrice/totalAssets/netExpenseRatio/funds_data`，A 股用新浪净值接口，走已有的 httpx），不需要新依赖。

其余工作归到两个配角栏目：**正确性**（Wilder RSI、港股/A 股货币、`--json`、若干小 bug）和 **说清楚 LLM 分工**（回应 issue #5 追评）。

## 2. 范围边界

**做**

- ETF：识别、基金画像、对齐日期的溢价折价、不适用的大师弃权、ETF 体检清单、不写 learning；CLI / 报告 / MCP / Dashboard 四处展示。
- 正确性：Wilder RSI（PR #10 的修复，不收依赖）；大鱼波动率单位错配；港股/A 股金额换算成美元；`--json` 输出合法 JSON；fear-greed 标定；health 版本号；回测页伪造指标；分歧图"strong majority"；Kelly 口径不一致；Communication Services 判为科技；EDGAR 覆盖后证据不同步。
- LLM：README 新增"Augur 怎么用大模型"三种模式；修 `augur_configure` 死配置；删无人 import 的 `anthropic` extra；补环境变量表。

**不做**

- 不加第三方依赖；不给 ETF 新增第 19 位"大师"（会牵动所有"18 位"计数和技能生成）；不做 LLM 写作功能；不 push、不打 tag、不发 PyPI（`v*` tag 会触发 `publish.yml`，另行决定）。

**推迟到 v14.x**（第 4 节列原因）

- 真 True Range 的 ATR 与 Munger / Dalio 阈值重校；MACD 种子约定；波动率样本方差；`beta_1y` 改名；死字段（`stoch_k`、`max_drawdown` 等）。
- 回测保真度：`backtest.py:167-169` 只传 rsi/macd、缺失前瞻收益填 0、`learning.py:362` 入场价前视（后两条未核实）。
- risk-review 改写识别（`risk_review.py:337` 起）；`earnings --backfill` 把下调指引 8-K 当财报。
- `augur memo`（LLM 只写散文）；Dashboard 的 模板/LLM 来源标记。
- ETF 历史溢价与跟踪偏离（东财净值历史）；A 股 ETF 的持仓/费率；清理 learning 里已有的 ETF 旧记录（记录没有资产类型标记，无法离线判定）。

## 3. 步骤（按风险从高到低）

统一约定：在分支 `v14` 上做，各工作流用独立分支；只提交自己改的路径；测试不联网。

全量验证命令（下称"全量"）：`.venv/bin/python -m pytest tests/ -q --tb=short -p no:cacheprovider` 与 `.venv/bin/python -m ruff check src/`。

### 步骤 0｜契约（串行，先做，约 30 分钟）

- 文件：`src/augur/personas/base.py:69`（`MarketContext`）与 `:199`（`to_dict`）；新建 `src/augur/etf.py`。
- 做法：
  - `MarketContext` 新增 `asset_type: str = "equity"`、`etf: Dict = {}`、`financial_currency: str = ""`、`fx_rate_usd: float = 0`（交易货币兑美元，0 = 未知）。
  - `etf.py` 先只放契约：`etf` 字典的键（`aum_usd_bn, expense_ratio, yield, category, nav, nav_date, nav_date_inferred, premium_pct, top10_weight, hhi, sector_weights, asset_classes, turnover, spread_pct, dollar_volume, source`）、`is_fund(ctx)`、`FUND_APPLICABLE_PERSONAS`、`assess_etf(profile) -> List[finding]` 的签名。
  - **基线快照**：在 main 上用 4 个固定的手工上下文（AAPL 式大盘、小盘成长、港股、空上下文）跑全部大师，把分数/信号/findings 存成 `tests/fixtures/v13_persona_baseline.json`。后面"股票结果不变"的断言都对它比，不靠联网重跑。
- 验证：全量仍是 3615 passed；`MarketContext(ticker="X").to_dict()["asset_type"] == "equity"`。
- 依赖：无。其余工作流都从这个提交分叉。

### 步骤 1｜ETF 弃权与共识（工作流 C，风险最高）

- 文件：`src/augur/personas/base.py:216`（`BaseAgent`）、`src/augur/etf.py`、`src/augur/consensus/engine.py:21`、`:425-450`（learning 写入）、`src/augur/cli_commands/analysis.py:72,84`。
- 为什么不在 `registry.analyze_with_all` 过滤：仓库里有约 30 处直接调 `agent.analyze(ctx)`（`mcp_server.py:389,411,654`、`workflow.py:275`、`cli_commands/{analysis,monitor,workflow}.py`、`dashboard/routes/{committee,personas,ws}.py`、四个 bot、`backtest.py`），只守一个入口会漏。
- 做法：
  - **唯一守卫点**：`BaseAgent.__init_subclass__` 包一层子类的 `analyze`——`is_fund(ctx)` 且该大师不在适用名单时，直接返回"不适用于基金"的中性结果（`coverage_confidence=0`、`metadata.not_applicable=True`），不执行原规则。18 个 persona 文件和 `YamlAgent`（`persona_loader.py:142`）都不用改。
  - 数据层配合（步骤 3）：基金的 `pe/pb` 挪到 `etf["portfolio_pe"/"portfolio_pb"]`，`ctx.pe/pb` 留 0，公司估值规则无从触发。
  - **适用名单由"分数不变性"测试裁定**，不靠关键词：在 ETF 上下文上扰动公司字段（pe、pb、roe、毛利、营收增速、fcf、负债率、market_cap、机构持股），大师分数不动才算适用。按字段引用统计，预期只有 dalio 通过（纯技术字段）；marks 引用 `pe` 12 次、soros 引用 `revenue_growth` 6 次、arps 引用 `market_cap` 5 次，大概率不通过。把它们改成"识别基金"的版本推迟到 v14.1。
  - **因此 v14.0 的 ETF 输出定为**：ETF 概况 + 体检清单 + 适用大师各自的技术/风险读数。适用大师少于 3 位（含 `enabled_personas` 全部不适用的 0 位情况）时**不出共识信号**：引擎返回中性、置信度 0、`metadata.consensus_withheld=True`，CLI 明写"适用大师 N 位，不输出共识"。不给 Kelly 仓位。
  - 引擎在加权前剔除 `not_applicable` 的结果；ETF 不 `record_prediction`（并入现有 `context_is_empty` 判断）。
  - `assess_etf`：确定性体检（费率偏高、规模 < $50M 清盘风险、|溢价| > 1%、前十大 > 50%、价差偏宽），只出结论清单，不进打分。
- 验证：新 `tests/test_etf_consensus.py`——
  - 逐个大师直接调 `agent.analyze(etf_ctx)`：buffett / dan_bin / dayu / thiel 返回 `not_applicable`；
  - 分数不变性测试决定并锁定适用名单；
  - ETF 共识带 `consensus_withheld`，learning 记录数不变；
  - 股票上下文的全部结果与步骤 0 的基线快照一致。
  - 全量通过。
- 依赖：步骤 0。可与 A、B、D 并行（测试用手工上下文，不等数据层）。`base.py` 在步骤 0 之后只归 C。

### 步骤 2｜货币换算（工作流 A）

- 文件：`src/augur/datasources/yfinance_provider.py:100-119`、`src/augur/valuation.py:118` 附近（单币种假设）、`src/augur/cli_commands/valuation_cmd.py`。（`cli_commands/data.py:44,54` 写死的 `$` 归步骤 7。）
- 做法：
  - 读 `financialCurrency`。市值、EV 按交易货币换算，FCF/营收/EBITDA/现金/负债按财报货币换算，统一成"十亿美元"（各 persona 的市值阈值本来就按美元写）。股价保持交易货币。
  - 汇率来源：同一 yfinance 的 `<CCY>USD=X` 最近收盘，放进 provider 内一个可替换的 `_fx_to_usd(ccy)`，结果缓存；测试 monkeypatch 这个函数。
  - 取不到汇率时：不换算，`fx_rate_usd=0`，显示成"市值 (HKD)"并给一条数据警告，不静默当美元。
  - DCF 每股价值与股价比较前换成同一货币。
  - 注意影响面不止港股/A 股：美股 ADR（美元股价、非美元财报）的 FCF、营收也会被换算。
  - 离线约束：`scripts/readme_smoke.py` 会把被吞掉的联网尝试也判失败，汇率函数在冒烟的假数据层和现有港股用例里都要有假实现。
- 验证：新测试——腾讯样例（HKD 3.1 万亿、财报 CNY）得市值约 400、FCF 按 CNY 汇率；汇率缺失分支；USD 股票字段不变。实跑 `augur fetch 0700.HK` 市值约 $400B，`augur valuation 0700.HK` 不再出现 -68.9% 这类跨币种偏差。
- 依赖：步骤 0。与步骤 3 同在工作流 A，先后做。

### 步骤 3｜ETF 数据（工作流 A）

- 文件：`yfinance_provider.py:100-241`、`src/augur/data.py:392-430`（EDGAR 覆盖）、`:256-370`（证据生成）。
- 做法：
  - 读 `quoteType`；`ETF/MUTUALFUND` → `asset_type="etf"`。A 股兜底规则须带后缀：`.SS` 且 51/56/58 开头，或 `.SZ` 且 15 开头。备用数据源（stooq 等）和手工上下文默认 `equity`，只吃后缀规则；写进文档。
  - 填 `etf` 画像。溢价折价用 **NAV 对应日的收盘价**：yfinance 不给 NAV 日期，按上一交易日推断并置 `nav_date_inferred=True`，报告里照实写。
  - ETF 跳过 EDGAR 覆盖。
  - 顺手修 bug 4：`_overlay_edgar_fundamentals` 改值后同步更新对应 `evidence_items`（可砍）。
- 验证：新 `tests/test_etf_data.py`，mock 三份 info（SPY、2800.HK、510300.SS）；SPY 对齐后溢价约 -0.04% 而不是 -0.25%；`funds_data` 抛异常时画像降级而不是整体失败。实跑 `augur fetch SPY` 不再出现 Market Cap $0.0B / ROE 0。
- 依赖：步骤 0、2。

### 步骤 4｜Wilder RSI 与指标模块（工作流 B）

- 文件：新建 `src/augur/indicators.py`；`src/augur/data.py:1015-1126`（旧函数名保留为薄包装）；`scripts/data_fetcher.py:137-141`；`tests/test_data.py`。
- 做法：
  - 纯 Python Wilder 平滑：前 14 个变化取简单平均做种子，之后 `avg = (avg*13 + x)/14`。平盘序列返回 50，只涨不跌返回 100，数据不足返回 50。
  - PR #10 的两个测试原样加入。
  - `indicators.py` 本版只放 `sma / ema / wilder_rsi / macd`，MACD 与波动率算法不变，只搬家。
  - 历史窗口保持 3 个月（`yfinance_provider.py:164`）不动：63 根收盘下 Wilder 种子的残余权重不到 3%；改窗口会连带改变 MACD（EMA 以首根收盘为种子），本版不引入。
- 验证：`pytest tests/test_data.py -q` 通过，含 70.46 / 66.25 两个参考值与"先跌后震荡 < 50"；`test_data.py:121`、`:128`、`test_backtest_live_default.py:63` 保持通过；对基线快照只有 RSI 相关项变化；全量通过。
- 依赖：步骤 0。与 A 共用 `data.py` 但区段不重叠（A 只动 1000 行以前，B 只动 1000 行以后）。

### 步骤 5｜persona 小修（工作流 B）

- 文件：`src/augur/personas/dayu.py:241-249,423,456`、`scripts/dayu.py:238,420,453`、`personas/custom/da-yu.yaml:67,70`、`src/augur/personas/thiel.py:264`。
- 做法：大鱼把小数波动率乘 100 再比（阈值不动）；Thiel 把 Communication Services 及互联网行业算作科技。
- 验证：新测试——`volatility_20d=0.65` 时大鱼风险分下降；GOOGL 样例不再出现"非科技行业"。
- 依赖：无。

### 步骤 6｜A 股基金净值（工作流 A 的最后一步，可砍）

- 文件：新建 `src/augur/datasources/cn_fund_nav_provider.py`。
- 做法：httpx 请求 `hq.sinajs.cn/list=f_<code>`（需 Referer），取单位净值和净值日期，补进 `etf.nav / nav_date`。失败静默降级。冒烟与测试里同样要有假实现，不能真连网。
- 验证：用录制的响应文本做解析测试；实跑 `augur fetch 510300.SS` 显示净值日期与溢价。接口不稳就整步砍掉，A 股 ETF 只做到"识别 + 弃权"。
- 依赖：步骤 3。

### 步骤 7｜输出面（工作流 C）

- 文件：`src/augur/cli_helpers.py:27-30`、`src/augur/cli_commands/data.py:27,40-60`、`src/augur/report.py:300` 附近、`src/augur/mcp_server.py:263-290`（手工上下文加 `asset_type` 参数）与 `:498-531`、`src/augur/consensus/engine.py:159,317`、`src/augur/cli_commands/monitor.py:145`。
- 做法：
  - 进度提示改 `err=True`，`--json` 时 stdout 只有 JSON。
  - fetch / consensus / report 对 ETF 输出"ETF 概况 + 体检"，隐藏公司基本面行。
  - `cli_commands/data.py:44,54`：金额按美元显示；股价带交易货币；汇率未知时标"市值 (HKD)"。
  - `augur_configure` 写的配置没人读：改为明确返回"Augur 不调用模型，此设置无效"，并在文档标注弃用。
  - 中性信号的 Kelly 仓位统一为 0（engine 与 monitor 一致）；`engine.py:159` 的科技判定同步骤 5。
- 验证：`augur consensus AAPL --json 2>/dev/null | python -m json.tool` 成功（analyze、fetch、`portfolio --format json` 同）；`tests/test_cli.py` 新增对应断言。
- 依赖：步骤 0、1。

### 步骤 8｜Dashboard 与杂项（工作流 D）

- 文件：`src/dashboard/routes/market.py:421`、`src/dashboard/routes/misc.py:79`、`src/dashboard/routes/backtest.py:76-90`、`src/dashboard/routes/analysis.py` 与个股模板、`src/augur/disagreement.py:376`、`pyproject.toml:56`、`src/augur/chat.py:5-6`（docstring 说不需要 LLM，已过时）、`docs/agent-integration-guide.md:65-68,135,147-154,201,218-227`（`./skills/buffett` 路径与 `openclaude.yaml`；中英）。
- 做法：
  - fear-greed 重新标定（VIX 28 应落在恐惧区），附测试表：VIX 12 / 20 / 28 / 40。
  - health 版本读 `augur.__version__`。
  - 回测页由命中率套公式得出的回撤/波动/Sharpe 改为 `null` 并显示"未实测"。
  - "strong majority" 改为要求占全体过半。
  - 个股页加 ETF 概况卡。
  - 删 `anthropic` extra；修文档里错误的 skill 路径和不存在的 `openclaude.yaml`。
- 验证：`pytest tests/test_market_endpoints.py tests/test_backtest_dashboard_ux.py tests/test_disagreement.py -q`；`augur serve` 后 `curl /api/health` 显示 14.0.0；ETF 卡截图。
- 依赖：步骤 0。

### 步骤 9｜文档与发布（工作流 E，最后串行，单人）

- 见第 6 节。版本号：`pyproject.toml:7`、`src/augur/__init__.py:8`。`scripts/readme_smoke.py` 加一只假 ETF，并把命令换成分组写法。
- 验证：第 5 节。

### 并行工作流

| 工作流 | 步骤 | 独占文件 |
|---|---|---|
| A 数据层 | 2 → 3 → 6 | `datasources/*`、`data.py` 1000 行前、`valuation.py`、`valuation_cmd.py` |
| B 指标与大师 | 4、5 | `indicators.py`、`data.py` 1000 行后、`personas/*.py`（除 `base.py`）、`scripts/*`、`personas/custom/*` |
| C ETF 分析与输出 | 1 → 7 | `etf.py`、`personas/base.py`、`consensus/engine.py`、`report.py`、`cli_helpers.py`、`cli_commands/{data,analysis,monitor}.py`、`mcp_server.py` |
| D Dashboard 与杂项 | 8 | `src/dashboard/**`、`disagreement.py`、`pyproject.toml` extras、`chat.py`、`docs/agent-integration-guide.md` |

步骤 0 在前、步骤 9 在后，都是单人串行。合并顺序 B → A → C → D，每次合并后跑全量。

## 4. 行为变化与迁移

- **分数会变的大师**（RSI 改 Wilder）：arps、dalio、marks、munger、soros、serenity、dayu，以及自定义 `da-yu.yaml`。调研测算旧算法与 Wilder 平均差约 5.8 点，约一成窗口跨 30/70 分界。
- **大鱼**：波动率规则此前从不触发，修复后高波动票会被扣 1–3 分。
- **非美元标的**（港股、A 股，以及财报货币非美元的美股 ADR）：市值规则按美元生效，例如腾讯在 aschenbrenner 的分数由 5.28 降到约 4.62；小盘判断不再被放大 7–8 倍。FCF 收益率规则（buffett、dan_bin、li_lu、duan_yongping、dayu、thiel）在股价与财报货币不同的标的上会变。
- **中性共识的仓位**：`position_pct` 一律为 0（此前 analyze 给 0.6% 这类小仓位，portfolio 给 0）。
- **Thiel 与行业加权**：Communication Services（GOOGL、META、腾讯）算作科技。
- **ETF**：不再有 18 位大师的共识；输出概况、体检清单和适用大师读数，适用不足 3 位时不出共识信号（v14.0 预期只有 Dalio 适用）；不给仓位建议；不写 learning。`pe/pb` 对基金为 0，组合口径的值在 `etf` 字典里。
- **learning 数据**：schema 保持 2，不作废。旧 RSI 下的待结算预测照常结算（当时的判断是真实做出的）；已写入的 ETF 旧记录留在原处，在升级说明里写明会让相关大师的准确率混入少量噪声，清理工具推迟。
- **Breaking**：`--json` 时进度提示改走 stderr（依赖 stdout 提示文字的脚本要改）；`MarketContext.market_cap/fcf/revenue` 等对非美元标的含义变为美元；`[llm]` extra 不再装 `anthropic`；`augur_configure` 弃用；回测接口的三个风险指标变为 `null`。
- **为什么 ATR 推迟**：真 TR 会让 `munger.py:78`（>3%）和 `dalio.py:81-86`（<2 / >5）触发率整体上移，需要先用数据重校阈值；一天内做不扎实，宁可本版只换 RSI。

## 5. 完成定义

- 全量测试通过且数量不少于 3615 + 新增；`ruff check src/` 干净；`python scripts/readme_smoke.py` 全绿；测试期间无网络访问。
- 实跑（联网，人工看输出）：
  - `augur fetch SPY`：显示 ETF 概况（AUM 约 $797B、费率、溢价约 0、前十大占比），没有 ROE / 毛利行。
  - `augur consensus SPY`：列出适用与弃权的大师，明写不输出共识的原因，无"小市值""毛利率过低"。
  - `augur fetch 2800.HK`、`augur fetch 510300.SS`：识别为 ETF（后者有无净值取决于步骤 6 是否保留）。
  - `augur fetch 0700.HK`：市值约 $400B。
  - `augur consensus AAPL --json 2>/dev/null | python -m json.tool`：成功。
  - 基线快照对比（离线）：美元股票除 RSI 相关项、中性仓位、科技行业判定外无变化。
  - `augur serve`：`/api/health` 为 14.0.0；`/api/fear-greed` 在 VIX 28 附近不再显示 Greed；GET 巡检无 500。
- 截图（`docs/images/screenshots/v14/`，英文界面）：`etf-fetch.png`、`etf-consensus.png`、`dashboard-etf-card.png`；`cli-help.png` 有变化才重拍。
- 不打 tag：发布另行决定。

## 6. 文档更新清单

- `README.md` / `README_EN.md` / `README_JA.md`（三份结构一致，各 457 行）：
  - 徽章与"v13 新功能一览"（:11、:40）改为 v14，第一条是 ETF 原生分析加两张截图。
  - 新增"Augur 怎么用大模型"一节（放在"为什么不一样"之后）：默认确定性规则、MCP 宿主当 LLM、自带 key 的聊天三种模式。对比表（:28-34）措辞同步。
  - "从 v12 升级到 v13"（:158）改写为"从 v13 升级到 v14"，内容取第 4 节。
  - 环境变量表（:342-352）补 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`AUGUR_CHAT_MODEL`。
  - CLI 速查与更新日志折叠块（:391）。
- `CHANGELOG.md`：`[14.0.0]`，分 Added（ETF）/ Fixed / Breaking / Deferred。
- `docs/ROADMAP.md`：新增"2026-11 阶段：v14"，记录步骤状态和推迟项；"文档与截图遗留"里勾掉 `readme_smoke.py` 一条。
- `docs/RELEASE_NOTES.md` 与 `docs/en/RELEASE_NOTES.md`；`docs/data-sources.md`（中英）加 ETF 字段、新浪净值接口、汇率来源；`docs/agent-integration-guide.md`（中英）；`docs/schema-reference.md` 加 `asset_type / etf`。
- 文档用中文，代码与 commit 用英文；文档不写模型或工具为作者。
