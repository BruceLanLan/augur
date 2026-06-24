# Augur Next v9 — 开发路线图

> 本文件是 augur-next 的开发计划，供新 session 快速恢复上下文。
> 最后更新：2026-06-24，当前版本 **v10.16.6**（事件循环阻塞 bug 从首页 widget 延伸到投委会/深度报告，覆盖 19 个 handler，2095 tests passing，含网络测试 2100；**但实测发现投委会/深度报告这部分只是大幅缓解，没有彻底解决——CPU 计算受 GIL 限制，其他并发请求仍会被拖慢 3 秒以上，详见下方叙事和 CHANGELOG**）

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

**当前能力盘点（v10.16.6）：**
- MCP 工具 13 个：analyze, consensus, committee, debate, fetch, sentiment, list_personas, configure, create_persona, workflow, **workspace_get, workspace_set, workspace_profiles**
- CLI 命令：analyze, consensus, report, serve, watch, skills, portfolio, backtest, chat, sentiment, inject-soul, telegram, slack, wechat, lark, cron-* 等
- Dashboard 19 页（含 committee, hermes-setup），委员会页已接入工作区配置
- 19 个 skill 目录（SKILL.md + manifest.json），版本号与 `augur.__version__` 自动同步
- i18n：中/英/日/韩四语言，降级链，workspace profile 9 key × 4 语言全部完整
- `augur_workflow` 默认步骤跟随终端布局预设（P2-7），定制化与 agentic 行为联动
- 投资委员会 Kelly 仓位显示已修复（v10.16.4），与 Deep Report 数字一致
- 首页仪表盘事件循环阻塞 bug 已修复（v10.16.5）：11 个相关接口改为同步 def，板块行情补上并行抓取+超时
- 投委会/深度报告自己的事件循环阻塞 bug 已**大幅缓解但非彻底修复**（v10.16.6）：再加 8 个接口改为同步 def，2 个 WebSocket 接口的阻塞调用丢进线程池，回归测试覆盖 19 个 handler——但实测发现 18 位大师的 CPU 计算受 Python GIL 限制，投委会运行期间其他并发请求仍会被拖慢 3 秒以上，详见下方叙事和 CHANGELOG「已知局限」
- 测试基线：**2095 passed, 0 failed**（不含 5 个网络测试；含网络测试共 2100）

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

**P2-3/P2-4 方法论澄清：** 用户已明确授权对 P2-3（regime 检测 hysteresis）和 P2-4（统一 OOS 校准管道）跳过"先观察再设计"的默认原则，直接设计实现——这是针对这两项的一次性授权，不代表"观察先于设计"方法论本身改变。

**下 session 待定：** 向用户确认 v10.16.5+v10.16.6 修复是否真的改善了体验（仪表盘可点击、数据正常显示、投委会/深度报告不再彻底卡死——但已知投委会/深度报告生成期间其他请求仍会有数秒延迟，这是已记录的限制，不需要每次都重新发现）；如果用户后续想彻底解决 GIL 拖慢问题，可从「给 18 位大师的 analyze() 做 profile 提速」或「换成进程池/多进程绕开 GIL」两个方向继续；P2-3（regime 检测加 hysteresis + 历史回测验证，已获用户授权直接设计）仍是 synthesis 文档中唯一标注的"不要把共识结果当风险输入"地基类风险，功能 backlog 内优先级最高；P1-9（dashboard router 拆分）、P2-1/P2-2/P2-4/P2-5/P2-6/P2-8 待选；用户分享了参考站点 chanlun.oldorange.club 作为产品形态参考，尚待讨论；v10.16.4 是本地 commit（`66f7424`），尚未推送到 origin；v10.16.5 和 v10.16.6 目前都**还没有 commit**，全部停留在工作区改动（`git status --short` 66 个文件），需用户明确指示才能 commit，commit 后还需用户明确指示才能 push。

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
