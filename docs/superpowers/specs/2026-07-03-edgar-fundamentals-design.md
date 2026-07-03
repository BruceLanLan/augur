# SEC EDGAR 基本面数据深化 — 设计文档

**日期**：2026-07-03
**状态**：已批准设计，待拆实施计划
**所属战略主线**：数据 → 可信度 → 发布（三阶段路线图的第一阶段）

## 背景

Augur 目前有 18 位投资人 persona，各自的打分依赖 `MarketContext` 里的基本面字段（pe/pb/roe/gross_margins 等），这些字段全部来自 yfinance 的简化比率。P2-4（v10.16.9）曾用 yfinance 年报数据搭过一版"时点基本面" provider（`pit_fundamentals.py`），用于验证 regime 权重是否有效，但受限于 yfinance 年报数据的保留期，历史只能回溯到约 2022 年，且滞后归档日是靠 90 天保守缓冲猜的，不是真实 filing 日期。

本设计的目标是用 SEC EDGAR 官方免费接口替换这套简化方案，同时服务两个目的：

1. **提升实时分析质量**——今天跑 `augur analyze AAPL` 时，18 位大师能看到真实财报细项、内部人交易、机构持仓变化、管理层前瞻文本，而不只是几个简化比率。
2. **扩展回测历史覆盖深度**——用 EDGAR 真实 filing 日期做时点纪律（而非猜测缓冲），历史覆盖能从 2022 拉回到 2010 年代早期，让未来的 regime 权重验证不再受限于"熊市高波动桶只有 9 天数据"这类欠势问题。

**范围边界（明确排除）**：SEC EDGAR 只覆盖美股上市公司（含在美上市的中概股 ADR，如 BABA/PDD），不覆盖纯 A 股、港股、加密货币标的。这些标的继续使用现有 yfinance 简化比率方案，不受本设计影响。

## 整体架构

```
src/augur/consensus/
  edgar_fundamentals.py   # 阶段1：XBRL 财报（新，取代 pit_fundamentals.py）
  edgar_insider.py        # 阶段2：Form 4 内部人交易
  edgar_institutional.py  # 阶段3：13F 机构持仓
  edgar_guidance.py       # 阶段4：指引文本 LLM 抽取（默认关闭）
```

四个阶段共用 `edgar_fundamentals.py` 里的 `EdgarClient` 基础设施：

- **CIK 映射**：EDGAR 用 CIK（Central Index Key）标识公司，不是股票代码。拉 EDGAR 官方 `company_tickers.json`（全市场 ticker↔CIK 映射表），本地缓存，定期刷新。
- **限流**：SEC 强制 10 req/sec 上限，且每个请求必须带 `User-Agent: <项目名> <联系邮箱>`，否则会被拒绝或封禁。实现一个简单的 token-bucket 限流器；联系邮箱走环境变量 `AUGUR_EDGAR_CONTACT_EMAIL`，提供一个占位默认值但在文档中明确要求用户自行设置（SEC fair-use 政策要求真实可联系的邮箱，用占位默认值长期使用有被封禁风险）。
- **缓存**：`~/.augur/edgar_cache/`，与现有 `~/.augur/`（history/、feedback/、learned_weights.json）目录约定一致。
- **降级路径**：非美股标的、CIK 匹配失败、EDGAR 接口异常时，一律 `never raises`，优雅返回"不可用"标记，上层自动降级到现有 yfinance 逻辑。这是贯穿全部四个阶段的统一原则，不是阶段 1 独有。

## 阶段 1：XBRL 财报基础设施（取代 pit_fundamentals.py）

### 数据源

EDGAR `companyfacts` API，`us-gaap` taxonomy 下的标准财务概念：`Revenue`（或 `RevenueFromContractWithCustomerExcludingAssessedTax` 等历史演变过的标签变体）、`NetIncomeLoss`、`StockholdersEquity`、`Assets`、`Liabilities`、`GrossProfit`、`OperatingIncomeLoss`。每个概念的 XBRL 返回值自带 `filed`（filing 提交日期）和对应报告期，天然带时点信息，不需要像 yfinance 方案那样另外猜测归档滞后。

### 实时分析集成

`MarketContext` 的 `pe/pb/roe/gross_margins/revenue_growth/debt_ratio` 等字段保持字段名和语义不变，取值来源变成"EDGAR 优先，缺失或非美股时降级到 yfinance"。对 18 个 persona 的 `analyze()` 调用方式零改动——它们读的仍然是同一批 `MarketContext` 字段，只是字段背后的数据来源变得更真实。

### 回测集成

`src/augur/backtest.py` 里调用 `fetch_pit_fundamentals` 的两处（`run_live_backtest` 和 `compute_cross_sectional_regime_ic` 路径）改为调用 EDGAR 版本的等价函数，签名保持一致（`fetch_edgar_fundamentals(ticker, as_of_date, price) -> dict`，含 `insufficient` 标记）。`pit_fundamentals.py` 整体废弃删除，`tests/test_pit_fundamentals.py` 对应迁移/重写为 `tests/test_edgar_fundamentals.py`。

时点纪律沿用 P2-4 已验证的原则：只用 `filed_date <= as_of_date` 的最新一期数据；如果一期都没有，标记 `insufficient=True` 让上层跳过该日，绝不补零。

### 测试

- 合成 XBRL JSON response（离线，不联网），验证 look-ahead 守卫：`filed_date > as_of_date` 的期不被使用
- 多期数据下正确选取"最新的 as-of 可得"期
- 缺失概念（如某公司没报 `GrossProfit`）时该字段留空，不影响其他字段
- 非美股 ticker（CIK 匹配失败）正确降级，不抛异常
- EDGAR 接口异常（超时/限流/5xx）时正确降级，不阻塞整体分析流程

## 阶段 2：内部人交易（Form 4）

### 数据源与信号设计

EDGAR Form 4 filing 是结构化 XML，不需要 NLP。提取字段：filer 角色（高管/董事/10% 股东）、交易类型（买/卖，Table I 非衍生品交易为主）、股数、每股价格、交易日期。

信号：`insider_buying_signal`，计算方式为 trailing 90 天净买入金额（买入总额 − 卖出总额）除以同期日均成交额，做 0-10 归一化（0=大量净卖出，5=中性，10=大量净买入）。同一周内多个不同高管同时买入（聚集买入）时对信号做适度放大，因为这通常是比单个高管买入更强的信号。

### 集成方式

作为新增的独立 factor 写入 `metadata.factors["insider_buying_signal"]`，走跟现有约 70 个因子完全一样的路径（各 persona 的 `analyze()` 方法自行决定是否读取、如何加权）。同步更新 `src/dashboard/static/js/factor-map.js` 的 `_FACTOR_MAP`，新增该 key（初步倾向归入 `quality` 类目，或新增一个 `insider` 类目——留到实施阶段视实际因子数量决定）。

不绑定特定大师群体：不强制要求 Buffett/Graham 等价值派或 Soros/dayu 等动量派的打分逻辑必须使用这个新因子，是否使用、如何加权是各 persona 自己的实现细节，这次只负责把数据和因子接口铺好。

### 测试

- 合成 Form 4 XML，验证买入/卖出金额正确解析
- trailing 90 天窗口正确过滤（超窗口的交易不计入）
- 聚集买入放大逻辑
- 无 Form 4 filing 时信号返回中性值（5.0）而非 0 或异常

## 阶段 3：机构持仓变化（13F）

### 范围界定

不做全市场聚合（每季度上千份 13F filing，数据量和基础设施复杂度都不现实）。改为硬编码一份"知名机构"CIK 起步名单（Berkshire Hathaway、Renaissance Technologies、Bridgewater Associates、Scion Asset Management、Pershing Square 等 15-20 家），后续可通过配置文件扩展，不写死在代码里。

### 信号设计

`institutional_flow_signal`：追踪名单里每家机构在该标的上的季度环比持仓股数变化百分比（新增持仓视为 +100%，清仓视为 -100%），对名单内全部机构取简单平均（不按机构 AUM 加权——加权需要额外维护每家机构的资产规模数据，且"知名机构"名单本身已经是一种粗粒度筛选，简单平均足够作为第一版），映射到 0-10 归一化（5=名单整体持仓不变，10=名单整体大幅增持，0=名单整体大幅减仓）。13F 有法定 45 天披露滞后，时点纪律为 `available_from = 披露日期`（不是报告期末日期）。

### 测试

- 合成 13F filing 数据，验证季度环比增减计算正确
- 名单中机构本季度未持有该标的（清仓或从未持有）时的边界处理
- 45 天披露滞后的时点纪律验证

## 阶段 4：管理层指引/前瞻文本（默认关闭）

### 数据与处理

拉 10-K/10-Q 的 MD&A（Management's Discussion and Analysis）章节原文，调用现有 LLM 集成（`augur` 已有 `llm` optional dependency group，anthropic/openai）做结构化抽取：管理层展望情绪（正面/负面/中性）、具体前瞻指引数字（如有明确提及）、风险因子章节较上一期 filing 的变化摘要。

### 成本/延迟控制

默认关闭，用户需要显式开启（配置项，暂定 `augur config set edgar.guidance_extraction true` 或等价的环境变量，具体交互形式留到实施阶段确定）。同一份 filing 的抽取结果按 filing accession number 永久缓存到 `~/.augur/edgar_cache/`，绝不对同一份文件重复调用 LLM。

### 依赖隔离

独立于阶段 1-3：缺少 `llm` extras 或用户未显式开启该功能时，整个阶段跳过，不影响阶段 1-3 和其余系统功能。这与项目现有的 optional-dependency 隔离模式（如 `mcp`、`telegram` extras）一致。

### 测试

- LLM 调用路径用 mock，不在单测里真实调用（成本/网络原因）
- 缓存命中时不重复调用 LLM（用 mock 的 call_count 断言）
- 未开启该功能时整个阶段被跳过，不报错、不影响其他分析结果
- 缺 `llm` extras 时优雅降级（`ImportError` 被捕获）

## 实施顺序建议

阶段 1 是地基，必须先做。阶段 2/3 互相独立，可以并行或任意顺序。阶段 4 技术风险最高（依赖 LLM 抽取质量，且是四个阶段里唯一需要真实联网+付费 API 调用才能端到端验证的），放最后，且默认关闭意味着即使质量不够理想也不会影响默认用户体验。

## 明确不做的事（本次范围外）

- 不支持非美股标的的类似深度数据（A股需要接巨潮资讯/东方财富之类的数据源，港股需要接港交所披露易，都是完全不同的数据源和法规体系，不在本次范围内）
- 13F 阶段不做全市场聚合，只做知名机构名单跟踪
- 阶段 4 不做实时监控/推送（如"某公司刚发布新 10-Q，前瞻文本转为负面"），只在用户主动分析时按需抽取
- 不改动任何现有 persona 的打分逻辑本身——本设计只负责把新数据和新因子接口铺好，18 位大师各自要不要用、怎么用新增的 EDGAR 因子，是后续独立的 persona 调优工作，不在本次范围内
