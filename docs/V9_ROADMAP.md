# Augur Next v9 — 开发路线图

> 本文件是 augur-next 的开发计划，供新 session 快速恢复上下文。
> 最后更新：2026-06-25，当前版本 **v10.16.9**（P2-4：点时财务数据 + regime 权重样本外验证，2104 tests passing（不含本次新增 16 个离线测试时为 2120）；synthesis 文档那条 gate 的两半至此都已处理完——翻转抖动已消除（P2-3），手工权重数字本身经真实样本外数据验证后**没有看出稳定提升**（P2-4，结果是打平，不是"验证通过"也不是"证伪"）；v10.16.6 的投委会/深度报告 GIL 限制仍按用户决定保留为已知局限，详见下方叙事和 CHANGELOG）

---

## 总目标

把 Augur 打造成**专业的 Bloomberg AI Agent 系统**：
- 18 位投资人风格的独立 Agent
- 易于任何人接入（网页版 / Agent 版 / CLI）
- 及时更新、用户可高度 DIY
- 接入 OpenClaw / Hermes Agent 等
- 编程成一个独立 App

**仓库分工：**
- `augur`（github.com/BruceLanLan/augur）= 稳定版，当前 **v8.2.3**（公开，227★/34 fork，最后一次发布 2026-06-08——已落后 augur-next 两个以上大版本）
- `augur-next`（github.com/BruceLanLan/augur-next）= 开发版，当前 **v10.16.4**
- 本地：`feature/v9-dev` 分支跟踪 augur-next/main
- 推送命令：`git push augur-next feature/v9-dev:main`
- **下一里程碑：** 把 augur-next 稳定功能挑选打包，正式发布一版到公开 `augur`（见下方"公开发布准备"）

---

## 已完成（v9.0.0 → v9.0.6）

| 版本 | 内容 |
|------|------|
| 9.0.0 | 18位独立 Hermes Agent skill + `augur_committee` MCP 工具 + Dashboard 委员会页 |
| 9.0.1 | 18位专属人格化 system prompt（中国4位全中文） |
| 9.0.2 | 委员会预设（5种）+ `augur_sentiment` MCP 工具 + augur-next README |
| 9.0.3 | `/hermes-setup` 引导页 + 委员会会话存历史 + API 文档 + EN README |
| 9.0.4 | OpenClaw manifest.json(19) + install.sh + Makefile v2 + Docker v9 + `.mcp.json` + CLI `serve/watch/skills/portfolio` |
| 9.0.5 | create_persona DIY（预设+YAML预览+ID校验） |
| 9.0.6 | PWA 支持（可安装为独立 App） |
| 9.0.7 | stocks 历史共识走势折线图（Chart.js）+ README 准确性修复 |
| 9.0.8 | `augur committee` CLI 命令 + `augur update` 自更新 + compare 雷达图 + committee WebSocket 流式 + OpenClaw 文档 + PyPI CI |
| 9.1.0 | UI P0-P4 全完成：CSS token 统一 + 亮色模式修复 + 图表主题联动 + Tape 暂停 UX + 历史图点击 + Toast 升级 + Empty State SVG |
| 10.0.0 | v10 首发：日语/韩语 i18n（181 key × 2）+ 四语言循环切换 + 降级链 + Agent Detail Modal |
| 10.1.0 | 因子细分表 + History 搜索/筛选 + Settings 外观设置 + Portfolio/Watchlist CSV 导入导出 |
| 10.2.0 | Performance IC 柱状图 + CSV 导出（Performance/Backtest/Scanner 三处） |
| 10.3.0 | Signals CSV 导出 + Debate 辩论记录复制/下载 MD |
| 10.4.0 | Committee 报告复制/下载 + Optimizer 权重 CSV 导出 |
| 10.5.0 | Chat 对话导出 MD + Clear 清除功能 |
| 10.6.0 | History 分析日历热力图（GitHub 风格，绿/红/橙，点击日期筛选） |
| 10.7.0 | Stocks 最近分析 chips（localStorage）+ URL 状态同步（pushState） |
| 10.8.0 | 键盘快捷键帮助 Modal（`?` 键触发，四语言 i18n，Esc/背景关闭） |
| 10.9.0 | `augur-mcp` 独立 stdio 入口 + Hermes Studio / Claude Desktop 接入文档 |
| 10.10.0 | `hermes-agents/` 18 个预生成 agent YAML + skills manifest 全部更新为 `augur-mcp` |
| 10.11.0 | Compare 因子级雷达作用域 bug 修复 + 因子明细展开（mini 进度条，分类分组） |
| 10.12.0 | Scanner + Stocks 一键加入自选股（`/api/watchlist/add`，实时 toast 反馈） |
| 10.13.0 | Signals/History Ticker 列变导航链接 → `/stocks?ticker=X` 一键重新分析 |
| 10.14.0 | Terminal Workspace 布局预设 + Settings UI + `/api/workspace`；`augur_workflow` MCP 工具；`augur.consensus.*` 共识增强模块 |
| 10.15.0 | v10.14 功能正式发布 + **Agent Peer Review** 集成：persona 权重重归一化、服务端 landing 302、workflow 去重/low_participation；`scanner/` legacy；synthesis backlog |
| 10.16.0 | **P1-1 MCP Workspace 工具**：`augur_workspace_get/set/profiles`（agent 可读写用户的 Dashboard 布局/启用人格，闭合 agentic 接入缺口）；代码审查 4 项修复（registry.py `concurrent.futures.TimeoutError` 漏捕获、meta_model 混合权重可配置化 `consensus.meta_model_weight`、macro_features.py 缓存加锁、缺失的 `beautifulsoup4` dev 依赖）；新增 manifest-sync 回归测试（AST 校验 `.mcp.json` 与 `@mcp.tool()` 一致）；README/RELEASE_NOTES 公开发布文档重写 |
| 10.16.1 | **P1-4 committee_preset 接线**：`/committee` 页面加载时读取 `/api/workspace`，自动套用保存的委员会预设；**P1-2 manifest/Hermes yaml 版本同步**：18 个 persona 的 `manifest.json`/`SKILL.md`/`hermes-agents/*.yaml` 从硬编码旧版本号改为动态读取 `augur.__version__`，工具说明从 5/13 补全为 13/13；纠正此前误判为"未完成"的 P1-3（i18n 已完整）、P1-5（enabled_personas 多选 UI 已存在）两项文档状态 |
| 10.16.2 | **P1-6 workflow 局部失败容错**：`augur_workflow` 的 analyze/consensus/committee 任一步骤抛错时捕获为 `{"error": ...}`，其余步骤继续执行而不中断整条流水线；同步修复 `format_workflow_summary()` 在步骤结果为 error 形态时的 KeyError，新增"Step Errors"摘要小节；**P1-7 `/api/workspace` ETag**：支持条件请求，配置未变时返回 304；纠正此前误判为"未完成"的 P1-8（`USER_FEEDBACK_DIR` 用户反馈路径，已在 v10.15.0 落地） |
| 10.16.3 | **P2-7 `augur_workflow` 默认步骤跟随终端布局预设**：CLI `--steps` / MCP `augur_workflow` / HTTP `/api/workflow` 留空时不再固定走 `fetch,analyze,consensus`，改为查询当前激活 Profile 的 `layout_preset` 对应步骤（`workspace.LAYOUT_PRESETS[*]["workflow_steps"]`）：analyst=`fetch,analyze,consensus`，trader/minimal=`fetch,consensus`，committee=`fetch,analyze,consensus,committee`；显式传入 `--steps` 仍以传入值优先；`list_presets()` / `/api/workspace/presets` 同步暴露 `workflow_steps` 字段 |
| 10.16.4 | **用户实测发现的 bug 修复**：`/api/committee` 与 `/ws/committee` 把已经是百分数的 `position_pct`（半 Kelly 仓位，如 19.9 代表 19.9%）又乘了一次 100，导致投资委员会页面显示"1990.0%"这种荒谬数字；CLI/MCP/Deep Report 走另一套代码路径未受影响。两处统一改为直接使用原值，新增 2 条回归测试（断言 `kelly_pct <= 20.0`）。首页仪表盘不可点击、多页面数据缺失这两项用户反馈尚未复现——本环境无浏览器自动化工具，已用 curl/WebSocket 直测后端接口排除数据层问题，需要用户提供浏览器控制台报错或截图才能继续 |
| 10.16.5 | **用户实测发现的另两个 bug 根因定位+修复**：装好 Playwright + Chromium 后用真实浏览器复现，发现板块行情/加密货币总览/大宗商品/国债收益率/热门标的 5 个接口被误标成 `async def` 却内部做同步阻塞的 yfinance 调用——单进程 uvicorn 下任一个阻塞会卡住整个事件循环，拖住所有并发请求（包括用户点击触发的请求），这正是"首页点不动"+"数据不显示"两个反馈的统一根因。改为同步 `def`（Starlette 自动丢线程池执行）；板块行情额外补上线程池并行抓取+10s 超时（原来是逐个抓取无超时，实测 9.8s~15s+甚至完全超时）。用并发 curl 测试直接证明阻塞机制：修复前慢/快两个请求被拖到同时完成（~12.3s），修复后完全解耦（快请求恢复到 ~0.003s 基线）。**经 advisor 复查指出同类模式还残留在另外 6 个 handler**（单标的实时行情、搜索、7日迷你走势图、全球市场总览、涨跌幅领先、恐慌贪婪指数）——尤其是迷你走势图接口首页一次会并发发出好几个请求，是残留风险最高的一个——一并改为同步 `def`，回归测试覆盖范围扩大到全部 11 个 handler |
| 10.16.6 | **同一根因延伸到投委会/深度报告自己的代码路径——但实测只是大幅缓解，非彻底解决**：排查发现 `analyze_ticker`/`report_ticker`(深度报告)/`api_committee`/`api_compare`/`api_debate`/`compare_personas`/`get_persona_opinion`/`api_run_watchlist_analysis` 共 8 个接口同样是 `async def` 却函数体内零 `await`，内部同步调用 yfinance + 18 位大师同步分析；全部改为同步 `def`。`/ws/analyze`、`/ws/committee` 两个 WebSocket 接口因协议要求必须保持 `async def`，改用 `run_in_threadpool` 把阻塞的 yfinance 调用丢进线程池。顺手修了 `analyze_ticker` 里 `asyncio.get_event_loop().run_in_executor` 在转为同步函数后会静默失效的潜在 bug（换成普通后台线程）。回归测试覆盖范围从 11 个扩大到 19 个 handler。**但改完之后没有只看结构测试就收工，重新跑了真实并发压测，发现 18 位大师的分析是纯 CPU 计算，丢进线程池绕不开 Python GIL，投委会运行期间其他请求仍会被拖慢 3 秒以上**（有时比投委会自己耗时还长），已记录为已知限制，彻底解决需要给分析提速或换多进程，留给用户决定优先级 |
| 10.16.7 | **继续"数据不显示"排查到 Dashboard 剩余页面**：不再找 async/事件循环类问题，而是把 history/optimizer/portfolio/watchlist/scanner/signals/settings/chat 每个页面模板里的 `fetch()`/`fetchWithTimeout()` 调用对应到后端接口，逐个用真实 ticker 直接打到本地开发服务器上验证。找到两个真实缺陷：①历史页 52 周日历热力图请求 `/api/history?page=1&per_page=365`，但分页模式 `per_page` 上限是 100，超过直接 400，前端用空 `.catch()` 默默吞掉错误，日历卡片从未出现过——改成接口本身支持的 `limit=365` 非分页模式即可。②组合优化器内部用「每日收益率」却直接拿「年化无风险利率」去减，导致几乎所有资产的"超额收益"被算成负数——不仅显示的 Sharpe 比率离谱（实测 -1.44，正确应为 +2 左右），连最优权重的解析解公式本身都被污染，给出的持仓建议不可信；修复为先把年化利率换算成每日利率再用。完整测试套件 2100 个全部通过 |
| 10.16.8 | **P2-3（窄版）：regime 检测加 hysteresis + 历史时点取数**——synthesis 文档标注的唯一未解地基类架构风险，用户已授权跳过"先观察再设计"直接设计实现。该风险有两半：①regime 分类单日噪声就能抽风、②`_REGIME_ADJUSTMENTS` 手工权重数字本身是否有效从未验证——**这次只解决①，不碰②**（②留给 P2-4）。抽出纯函数 `classify_regime` 核心，实盘和历史回测共用同一份逻辑（结构上保证一致，非靠声明）：VIX 高低波动判定从硬切 25 改成非对称区间（进 25/出 23），新 regime 需连续 3 个交易日才被采纳。让一直是摆设的 `date_str` 参数真正生效，做无 look-ahead 的历史时点取数（顺手修了一个 bug：VIX/SPY 历史数据时区不同，导致日期对齐时序列对不上、历史回测会拿不到数据）。手动回测脚本（`scripts/regime_backtest_v2.py`，联网不进 CI）实测 2015-2026 共 2884 个交易日：翻转次数 389→101，"来回抽风"次数 146→10；2020 新冠崩盘/2022 熊市响应滞后仅 2-4 天，未变迟钝；2018 Q4 看似滞后两个月，查证后确认是旧方法被单日噪声误导（旧方法的 146 次抽风之一），新方法等到真正持续的 12 月选情才进场，符合设计预期。另验证了窗口长度无关性（SIDEWAYS 同时是 dwell scan 的种子态，只抽 SIDEWAYS 日期测不出"种子洗掉了"还是"种子根本没被挑战"，所以特意只抽非 SIDEWAYS 的日期，覆盖另外四种 regime，65/130/260 个交易日窗口分类结果一致）。新增 8 个离线确定性单测，完整测试套件 2108 个全部通过 |
| 10.16.9 | **P2-4：点时财务数据 + regime 权重样本外验证**——synthesis 文档那条 gate 剩下的另一半，验证 `_REGIME_ADJUSTMENTS` 手工权重数字本身是否真的提升预测质量。**动手前先发现一个更基础的问题**：历史回测从未给过任何一天真实的 PE/PB/ROE 等基本面数据（一直是 0），价值风格 agent（marks/graham 等）靠这些数字打分，喂常数 0 等于把它们的分数钉死成常数——常数分数不管怎么加权排序都不会变，意味着"验证权重是否有效"这件事在此之前是**无法验证的**（不是没做，是做了也等于白做）。新增 `src/augur/consensus/pit_fundamentals.py`：给定股票和历史日期，只返回当天"理论上已公布"的财报数据（90 天保守滞后），查不到就标记 `insufficient` 直接跳过，绝不补零。接入 `Backtester.run_live_backtest`。新增 `compute_cross_sectional_regime_ic`（`src/augur/backtest.py`）：按天把"平权"vs"`apply_regime_weights` 加权"两套共识对全市场排序，与未来 20 日实际收益算 Spearman 秩相关，按 regime 分桶汇总，并对熊市高波动桶做块自助法置信区间。新增 `scripts/regime_weight_oos.py`：37 只跨行业股票、2022-01~2026-06 真实联网跑一遍，**实测结果：五个 regime 桶里 delta 都很小且方向不统一，没有看出稳定一致的提升**——不下"权重有效"或"权重无效"的结论，老实报告"打平"。**过程中发现并修复两个 bug**：①雅虎财经最老一年的数据列超出保留期后整列变 NaN，但旧逻辑只看日期标签不看数值是否真实存在，导致这类日期会"成功"返回一套全零数据而不是正确标记 `insufficient`（已用真实历史数据复现：2022-08-30 修复前返回全零"成功"结果，修复后正确返回 `insufficient`）；②雅虎财经接口本身偶发性返回空结果（3 次全新进程调用，2 次正常、1 次全空，证实是对方接口不稳定不是代码问题），旧逻辑把每只股票的财报永久缓存"第一次抓到的结果"，不巧抓到那次空结果就会永久误判，改为最多重试 3 次才接受空结果为真。新增 `tests/test_pit_fundamentals.py` 16 个离线确定性单测，完整测试套件 2104 个全部通过（含新测试为 2120 个）。**诚实声明：** 熊市高波动桶样本天数极少（37 只股票里只有 9 天同时满足 regime 分类+至少 5 只覆盖真实财务数据），且这 9 天不是独立样本，集中在两小段历史事件（2024-08 日元套息平仓、2025-04 关税冲击），置信区间是机械计算结果，只能当方向性观察，不能当统计意义上的证据 |

**当前能力盘点（v10.16.9）：**
- MCP 工具 13 个：analyze, consensus, committee, debate, fetch, sentiment, list_personas, configure, create_persona, workflow, **workspace_get, workspace_set, workspace_profiles**
- CLI 命令：analyze, consensus, report, serve, watch, skills, portfolio, backtest, chat, sentiment, inject-soul, telegram, slack, wechat, lark, cron-* 等
- Dashboard 19 页（含 committee, hermes-setup），委员会页已接入工作区配置
- 19 个 skill 目录（SKILL.md + manifest.json），版本号与 `augur.__version__` 自动同步
- i18n：中/英/日/韩四语言，降级链，workspace profile 9 key × 4 语言全部完整
- `augur_workflow` 默认步骤跟随终端布局预设（P2-7），定制化与 agentic 行为联动
- 投资委员会 Kelly 仓位显示已修复（v10.16.4），与 Deep Report 数字一致
- 首页仪表盘事件循环阻塞 bug 已修复（v10.16.5）：11 个相关接口改为同步 def，板块行情补上并行抓取+超时
- 投委会/深度报告自己的事件循环阻塞 bug 已**大幅缓解但非彻底修复**（v10.16.6）：再加 8 个接口改为同步 def，2 个 WebSocket 接口的阻塞调用丢进线程池，回归测试覆盖 19 个 handler——但实测发现 18 位大师的 CPU 计算受 Python GIL 限制，投委会运行期间其他并发请求仍会被拖慢 3 秒以上，详见下方叙事和 CHANGELOG「已知局限」
- 历史页日历热力图、组合优化器 Sharpe/权重计算已修复（v10.16.7）：均为接口字段/单位不匹配类问题，不是事件循环阻塞类问题——详见下方叙事
- regime 检测已加 hysteresis + 历史时点取数（v10.16.8，P2-3 窄版）：`classify_regime` 纯函数核心，实盘/回测同一份逻辑；synthesis 文档那条"不要把共识结果当风险输入"gate 的翻转抖动那一半已解除
- 点时财务数据 + regime 权重样本外验证已完成（v10.16.9，P2-4）：`pit_fundamentals.py` 给历史回测提供真实、无 look-ahead 的财务数据；`compute_cross_sectional_regime_ic` + `scripts/regime_weight_oos.py` 实测 `_REGIME_ADJUSTMENTS` 手工权重对样本外排序质量**没有看出稳定一致的提升**——synthesis 文档那条 gate 的另一半至此已老实测过，结果是打平而非"验证通过"，详见下方叙事
- 测试基线：**2104 passed, 0 failed**（含本次新增 `tests/test_pit_fundamentals.py` 16 个离线测试时为 2120 passed）

### scanner/ 弃用说明

- `scanner/` 仅为向后兼容 shim，实现已迁移至 `src/augur/`。
- Dashboard、`augur.registry`、MCP、CLI 应只从 `augur.*` 导入。
- 详见 [`scanner/README.md`](../scanner/README.md)。
- 唯一保留的可选 legacy 引用：`scanner.ten_x_screener`（10x 因子 overlay，模块缺失时静默跳过）。

---

## Agent Peer Review（v10.15.0 起）

6 份 agent peer review（#1 Workspace、#2 Workflow、#3 Consensus、#4 Dashboard、#8 Agent Hosts、#9 Architecture）已汇总至 [`docs/AGENT_PEER_REVIEW_SYNTHESIS.md`](AGENT_PEER_REVIEW_SYNTHESIS.md)。

**v10.15.0 已落地 P0：**
- Persona-aware consensus weights（`restrict_weights_to_agents`）
- 服务端 landing redirect（`GET /` → `resolve_landing_url`）
- Workflow：`enabled_personas` 桥接、consensus 去重、`low_participation` 警告

**v10.16.0 已落地 P1-1：**
- MCP workspace 工具（`augur_workspace_get/set/profiles`）+ manifest 13-tool 同步回归测试

**v10.16.1 已落地 P1-2、P1-4，并纠正 P1-3/P1-5 的文档误判：**
- committee_preset 接线、persona manifest/Hermes yaml 版本同步
- P1-3（i18n）、P1-5（enabled_personas 多选）实际在 v10.14.0/10.15.0 就已完成，本次仅更新文档状态

**v10.16.2 已落地 P1-6、P1-7，并纠正 P1-8 的文档误判：**
- workflow 局部失败容错（per-step error envelope）+ `format_workflow_summary()` KeyError 修复、`/api/workspace` ETag 条件请求
- P1-8（`USER_FEEDBACK_DIR` 用户反馈路径）实际在 v10.15.0 consensus 第三轮就已完成，本次仅更新文档状态

**v10.16.3 已落地 P2-7：**
- `augur_workflow` 默认步骤跟随终端布局预设：CLI/MCP/HTTP 三个调用点的硬编码默认值 `fetch,analyze,consensus` 改为留空时查询活跃 Profile 的 `layout_preset`
- 把"定制化"（终端布局预设）和"agentic"（agent 调用 workflow 的默认行为）两条主线在执行层打通，而不只是 Dashboard 页面展示层面

**v10.16.4：用户真机实测发现投委会 Kelly 仓位显示 bug 并修复**（见上方表格行），同时用户反馈整体产品体验问题较多（首页仪表盘点不动、投委会/深度报告多处数据不显示），判断当前还不太像可面向用户的产品形态。

**v10.16.5：首页仪表盘点不动 + 数据不显示，根因定位并修复**（见上方表格行）。本 session 新装了 Playwright + Chromium（此前环境无浏览器自动化工具的限制已解除），用真实浏览器复现，确认根因是 5 个 widget 接口被误标 `async def` 却内部同步阻塞调用 yfinance，单进程事件循环被卡住拖累所有并发请求。用并发 curl 测试（慢接口 vs. 正常 ~3ms 的快接口）直接证明了阻塞机制，再用浏览器验证修复后全部 widget 在 15s 内加载完成、无卡死骨架屏。修完 5 个之后调用 advisor 复查，被指出同一根因模式在另外 6 个 handler（单标的实时行情/搜索/迷你走势图/全球市场总览/涨跌幅领先/恐慌贪婪指数）里也存在且未修——尤其迷你走势图接口首页一次会并发打好几个请求，是残留风险最高的一处，只是因为修复验证用的 sparkline 请求命中了缓存才没在第一轮测试里暴露出来。一并改为同步 def，回归测试覆盖范围扩大到全部 11 个 handler，文档/计数同步更新。

**v10.16.6：同一根因延伸到投委会/深度报告自己的代码路径**（见上方表格行）。报告 v10.16.5 完成前调用 advisor 复查，被指出之前的排查只扫了首页 GET widget，没检查投委会/深度报告这条 POST/WebSocket 路径是否也有同样的阻塞模式——而这恰好是用户最初反馈里点名的"投委会""Deep Report"问题，v10.16.4 当时只查到并修了那里的 Kelly 显示 bug，并没有排查过卡死问题（v10.16.4 的 Notes 里也写明"未复现仪表盘点不动/数据不显示"两项，但没有专门提到投委会本身是否会卡）。逐个核对 `dashboard/app.py` 里所有 `async def` 且内部直接调用 `fetch_market_context` 或投资大师分析的 handler，发现 8 个 REST 接口（单标的分析、深度报告、投委会、对决、辩论、人格对比、单人格观点、自选股批量分析）和 2 个 WebSocket 接口都中了同样的招。REST 接口直接改同步 `def`；WebSocket 接口因协议限制保持 `async def`，把阻塞调用用 `run_in_threadpool` 丢进线程池。过程中还发现 `analyze_ticker` 原来的 `asyncio.get_event_loop().run_in_executor` 一旦转成同步函数会静默报错失效，换成普通后台线程修掉。回归测试覆盖范围从 11 个扩大到 19 个 handler，完整测试套件 2095/2100 通过。

**这次没有止步于"结构测试通过就是修好了"。** 改完之后重启开发服务器，用真实并发压测复测（一边发投委会请求，一边并发打一个本来很快的接口）——结果发现：投委会运行期间，其他并发请求仍会被拖慢到 3.2~3.6 秒，有时甚至比投委会自己的处理时间还长；单独测 5 个并发快接口（不带投委会）完全正常，最慢 21ms，排除了线程池本身的问题。根因和 v10.16.5 不一样：18 位投资大师的 `analyze()` 是纯 CPU 计算而非网络 I/O，丢进线程池虽然脱离了事件循环，但 CPython 的 GIL 决定同一时刻只有一个线程能真正执行代码，一个线程长时间占着 GIL 做重计算会让其他线程严重挨饿（CPython 里有名的"GIL 护航效应"）。这次修复的真实效果是：把"整个服务器彻底卡死直到投委会跑完"变成"其他请求被拖慢但不会无限期卡住"——是真实进步，但不是用户最初反馈里"投委会/深度报告卡死"的彻底解决。

把这个发现和三条后续选项（只记录已知限制不再扩大改动 / 先给 analyze() 提速 / 换成多进程彻底绕开 GIL）摆给用户，用户选择了第一条：先如实记录为已知限制，不做更大的架构改动。已按这个方向把 CHANGELOG/RELEASE_NOTES/README/本文档的措辞从"已修复"改成"大幅缓解，非彻底解决"，并新增"已知局限"小节说明 GIL 护航效应和后续两个可选方向（性能优化 analyze()，或进程池/多进程绕开 GIL，后者需要解决跨进程共享 registry/coordinator 单例、缓存、限流计数器的问题）。**这也是第二次发现"自认为修完了"其实没有完全修完**（第一次是 v10.16.5 报告前的 advisor 复查），所以下一次复查前也应该先假设可能还有没扫到的同类角落，不要单凭结构测试通过就认定问题彻底解决。

把 v10.16.5+v10.16.6 提交到本地 git（commit `1e57649`，66 个文件，含发现并补上的 skills/hermes-agents 版本号同步问题）之后，用户说"继续"，没有进一步指明方向。判断依据：用户最初反馈的三项里，"很多地方的数据都没有显示"覆盖范围比已经处理的首页+投委会更广，Dashboard 还有约 19 个页面没有专门排查过；同时调用 advisor 确认了这个判断——继续原定的"实测找 bug"主线，而不是转去做 P2 backlog 或重新讨论 GIL（GIL 已经是用户明确决定暂缓的事项，不应该在没有新信号的情况下重新打开）。

**v10.16.7：继续排查 Dashboard 剩余页面的"数据不显示"问题**（见上方表格行）。这次没有再去找"async def 卡事件循环"这一类已经扫过两轮的模式，而是换了方法：把 history/optimizer/portfolio/watchlist/scanner/signals/settings/chat 每个页面模板里所有 `fetch()` 和 `fetchWithTimeout()` 调用对应到具体的后端接口，列成清单后逐个用真实 ticker 直接打到本地开发服务器上看返回结果——重点看错误响应、字段是否对得上、数值是否符合常识。大部分接口都没问题。找到的两个真实缺陷：①历史页日历热力图用的 `/api/history?page=1&per_page=365` 触发了接口自己的分页上限校验（`per_page<=100` → 400），错误被前端一个空 `.catch()` 默默吞掉，日历卡片从未渲染过，没有任何可见报错——这是和 v10.16.5/v10.16.6 完全不同性质的 bug：纯粹是前后端参数契约没对齐，不涉及事件循环或并发。改用接口本身已经支持的 `limit=365` 非分页模式即解决。②组合优化器把"年化无风险利率"直接拿来跟"每日收益率"做减法，单位不匹配导致几乎所有资产的超额收益被算成负数——这个错误不仅让显示的 Sharpe 比率离谱（实测 -1.44，正确量级在 +2 左右），更严重的是它直接污染了最优权重的解析解公式本身，意味着优化器给出的"最优持仓"建议从一开始就不是真正最优的。这是一个金融计算正确性 bug，而不是界面/接口可用性 bug，影响比表面看到的"数字不对"更深——会让用户基于错误的权重建议做出真实的资金分配决策。修复为统一把年化利率换算成每日利率（除以 252 个交易日）后再参与计算。完整测试套件 2100 个全部通过，未触及 v10.16.6 记录的 GIL 已知限制。

**P2-3/P2-4 方法论澄清：** 用户已明确授权对 P2-3（regime 检测 hysteresis）和 P2-4（统一 OOS 校准管道）跳过"先观察再设计"的默认原则，直接设计实现——这是针对这两项的一次性授权，不代表"观察先于设计"方法论本身改变。

**v10.16.8：P2-3 窄版落地。** v10.16.7 commit 之后用户说"按我们的目标和规划继续"，对照本文档与 synthesis 文档确认 P2-3 是 backlog 内优先级最高、且已获一次性授权可跳过观察先于设计的项目，于是切 Opus 先做设计（advisor 两轮分别指出"实盘/回测要走同一份纯函数核心而非靠声明保证一致"、"flip-count 单独看会有'冻死不动'的退化最优，要配响应性检查"、"窗口长度路径依赖要在回测里实测验证，不能假设洗掉"三点，均已纳入设计），用户确认范围为窄版（只做稳定+点时正确，不碰手工权重数字本身是否有效）后切回 Sonnet 写代码。实现：`classify_regime` 纯函数核心（VIX 非对称区间 25 进/23 出 + 3 日确认期 dwell scan），`_macro_from_market` 改用 `start`/`end` 做真正的历史时点取数（过程中发现并修复 VIX/SPY 历史数据时区不同导致序列对齐失败的 bug），缓存按 `date_str` 分键避免历史回测污染实盘缓存。手动回测脚本验证翻转次数 389→101、抽风次数 146→10，崩盘窗口响应滞后仅 2-4 天，2018 Q4 那次看似两个月滞后查证后确认是确认期正确过滤了单日噪声（非缺陷）；窗口长度无关性也已验证（首次抽样全落在 SIDEWAYS 种子态、测不出问题，advisor 指出后改成只抽非 SIDEWAYS 的日期重测，结果仍然一致）。新增 8 个离线确定性单测，完整测试套件 2108 个全部通过。**诚实声明：** synthesis 那条 gate 有两半，这次只解除"翻转抖动"那一半，"`_REGIME_ADJUSTMENTS` 手工权重数字本身是否真的有效"完全没碰，留给 P2-4——不要把这次当成"架构风险已解除"。

**v10.16.9：P2-4 落地，synthesis 那条 gate 的两半至此都已处理。** 动手前先用一个独立的、不进正式交付的核查脚本确认了 Task 3 式的轴线假设——单只股票的逐日 agent 分数变化主要由价格/技术面驱动，基本面在很长一段时间里是平的；价值/成长风格的真正分化只存在于"同一天、不同股票之间"的横截面差异里，不在"同一只股票自己的逐日波动"里（marks/graham 等的跨股票常年差距 ~9.9-10.0 分，远超单只股票自己的日间标准差 0.2-2.0 分）——这一假设成立，才能继续往下做（如果不成立，本该停下报告而非继续）。于是确认了验证 `_REGIME_ADJUSTMENTS` 只能走"横截面 IC"路径：同一天把全市场按平权 vs regime 加权的共识排序，分别和未来收益算秩相关，按 regime 分桶——而不是去看单只股票自己的逐日 IC（一年只更新一次的财务数据会让这条时间序列退化成阶梯函数，重新加权一个近似常数信号根本不可能移动它的排名）。

实现过程中，在 20 只股票、2022 年单一年度窗口的烟雾测试里，发现五个 regime 桶的 `delta_mean` **全部精确为 0.0**——这个异常没有被当成"巧合"放过，往下查到了根因：雅虎财经最老一年的数据列一旦超出完整保留期，整列数值会变成 NaN，但列的日期标签还在；旧的 `_available_periods` 只检查日期标签是否满足 90 天滞后保护，没检查这一列是否真的有数值，导致 2022 年这类"只有 NaN 老列能通过滞后检查"的日期，会"成功"返回一套全零基本面而不是正确报告"数据不足"——这正是点时财务模块本来要防止的"无法验证"问题在一个新边界情况下的复发：常数（全零）信号不管怎么加权排序都不会变，五个桶全是 0 正是这个根因的直接后果，而不是"权重真的没用"的证据。同一轮排查还独立发现了第二个 bug：直接对同一只股票连续三次、各自全新进程调用雅虎财经接口，两次返回正常数据、一次返回完全空结果——证实雅虎财经那端本身偶发不稳定；旧的缓存逻辑是"每只股票的财报只抓一次，永久缓存抓到的结果"，不巧抓到那次空结果就会永久把这只股票误判为"没有数据"，这对一次要跑 30-50 只股票、跨好几年的长流程是个实打实的隐患。两个 bug 修复后用同一个 2022 年单一年度窗口复测：几乎所有股票当年返回 0 条记录（这是**预期内的正确行为**，不是新 bug——2022 年的财报要到 2023 年 3 月才"理论上已公布"，所以纯 2022 年窗口本来就不该有几条可用记录）；换成 2022-01 到 2025-06 的跨年窗口后，各 agent 在不同股票上的分数恢复了真实的跨股票差异，不再是"一个 agent 给常数、其余全是 0"的退化模式。

正式跑 `scripts/regime_weight_oos.py`（37 只跨行业股票，2022-01~2026-06，真实联网）：**五个 regime 桶的 delta 都很小、方向不统一**（SIDEWAYS n=746 delta=+0.0009，BULL_LOW_VOL n=43 delta=+0.0005，BEAR_HIGH_VOL n=9 delta=+0.0081，BEAR_LOW_VOL n=8 delta=-0.0056，BULL_HIGH_VOL n=8 delta=-0.0073）——没有看出 regime 加权比平权稳定更好。per-agent 截面 IC 在 BEAR_HIGH_VOL 桶里给出更细的方向性读数：graham +0.086（符合"熊市更信 Graham"的假设），marks -0.030（这 9 天反方向，与假设不一致），dalio 0.000（基本面差异化不足，无法区分）。统计意义最强的 SIDEWAYS 桶（n=746）delta≈+0.0009，即平权与 regime 加权几乎没有差别。**额外的诚实提醒**：regime 是按全市场单日判定的标签，不是按股票判定的，扩大股票池只会增加"同一天的横截面覆盖密度"，不会增加"熊市高波动的天数"——本次熊市高波动桶全程只有 9 天满足"至少 5 只股票有真实数据覆盖"，而且这 9 天不是分散独立的样本，是集中在两小段历史事件里（2024-08-07~09 日元套息平仓抛售、2025-04-07~14 关税冲击抛售），块自助法在这种样本上算出的置信区间是机械计算结果，不是有统计效力的证据，脚本本身在输出里把这句话直接打印出来，不留给后续读者自己误读的空间。

`tests/test_pit_fundamentals.py` 新增 16 个离线确定性单测，覆盖 90 天滞后保护的边界（恰好 90 天、89 天）、pe/pb/roe/margin 算术、YoY 增长率、`insufficient` 路径，以及本次发现的两个 bug 各自的回归测试（NaN 老列不被误判为可用、空抓取重试后不污染缓存）。完整测试套件改动前后各跑一遍：2104 passed（不含本次新增测试）/2120 passed（含新增 16 个）/0 failed——本文档此前记录的 2108 这个基线数字本次未能精确对账（差 4 个），怀疑是跨 session 的日期/网络门控测试波动，不是本次改动引入的回归（本次改动只涉及 `pit_fundamentals.py`/`backtest.py`，未触碰任何既有测试文件，且 `--collect-only` 与 `passed` 数字完全一致，说明没有静默跳过）。**诚实声明：** synthesis 那条 gate 的两半都已经老实测过了——P2-3 解决了"分类会不会抽风"，P2-4 测了"手工权重数字本身有没有用"，**结果是打平**：不是"验证通过"，也不是"证伪权重设计"，是"这次终于把它放到真实数据里测了一遍，测出来看不出稳定一致的提升"。要不要保留/调整/去掉这些手工乘数，是产品决策，留给用户，不在本次结论范围内。

**下 session 待定：** P2-4 完成后 synthesis 文档那条"不要把共识结果当风险输入"的 gate 两半都已处理完，可以考虑在文档里把这条 gate 标记为"已完整复核（结果：regime 分类稳定，手工权重效果中性）"，但不要写成"已修复"或"已验证有效"这类会被误读的措辞；P1-9（dashboard router 拆分）、P2-1/P2-2/P2-5/P2-6/P2-8 仍待选；GIL 护航效应已知限制（v10.16.6）仍按用户决定保留，未重新打开；v10.16.4 是本地 commit（`66f7424`）；v10.16.5+v10.16.6 已合并 commit 为 `1e57649`；v10.16.7 已 commit 为 `9508b03`；v10.16.8（P2-3 窄版）、v10.16.9（P2-4）均尚未 commit，停留在工作区，留给用户审阅后自行提交。所有 commit 都**尚未推送到 origin**，需用户明确指示才能 push；公开的 `augur` 仓库不要碰，除非用户明确说要碰。

---

## 待办（下个 session 从这里开始）

## 已全部完成 ✅

### P1 — 核心增强（全部完成）

- ✅ stocks 历史共识走势图（Chart.js 折线图）
- ✅ `augur update` 自更新命令
- ✅ 委员会 WebSocket 流式输出（/ws/committee，逐个大师意见实时渲染）
- ✅ Agent 对比雷达图（compare.html，5 维度 Chart.js radar）
- ✅ `augur committee` CLI 命令（preset + 自定义 agents）

### P2 — 生态扩展（全部完成）

- ✅ OpenClaw 接入文档（docs/openclaw-setup-guide.md + docs/en/）
- ✅ PyPI 发布准备（classifiers + GitHub Actions OIDC publish workflow）
- ⏭ Electron/Tauri 桌面 App（PWA 已作为轻量方案存在，跳过重型方案）

### P3 — 打磨（全部完成）

- ⏭ README 截图更新（页面功能已稳定，截图可在 v10 前做）
- ✅ WebSocket 集成测试（committee WS 4 个测试用例，1656 passed）
- ⏭ 日语/韩语 i18n（面向亚洲市场扩展，列为 v10 计划）

---

## v10 进展

- ✅ **日语/韩语 i18n**（v10.0.0）— 四语言循环切换，181 key × ja/ko，降级链
- ✅ **Agent Detail Modal**（v9.1.0 后提交）— stocks 页 scorecard 点击展示详细推理
- **README 截图更新** — 委员会页、hermes-setup 页、compare 雷达图实际截图
- **Electron/Tauri 桌面 App** — PWA 已作为轻量独立 App，v10 考虑 Electron
- **PyPI 正式发布** — 完成 OIDC trusted publisher 配置后 `pip install augur-agents`
- **因子级雷达** — 在 compare 页面对每个大师拆解到真实因子分（需 API 层改造）

---

## 关键约定（新 session 必读）

1. **每次改完跑测试**：`python3 -m pytest tests/ -q --tb=no --ignore=tests/test_analyze_api_v12.py 2>&1 | tail -5`（test_analyze_api_v12 需要网络，本地跳过）
2. **版本号同步改 3 处**：`src/augur/__init__.py`、`pyproject.toml`、README badge
3. **test_docs_audit_r13a.py 已改成版本无关**，不用每次改版本号都动测试
4. **文档要同步**：改功能必须同步 README.md + README_EN.md + CHANGELOG
5. **推送**：`git push augur-next feature/v9-dev:main`（不要推 origin/augur，那是稳定版）
6. **soul.py**：persona markdown 在 `docs/knowledge/personas/*.md`，不是 `personas/`
7. **agent 任务切小**：一个 agent 一件事，避免 session limit 中断丢工作；中断后先 `git status` 确认是否落地

---

## 快速恢复命令

```bash
cd ~/augur
git checkout feature/v9-dev
git log --oneline -5              # 确认在最新版本（见本文件顶部）
git status                        # 确认工作树干净
python3 -m pytest tests/ -q --tb=no --ignore=tests/test_analyze_api_v12.py 2>&1 | tail -3
```
