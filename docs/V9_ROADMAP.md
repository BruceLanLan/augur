# Augur Next v9 — 开发路线图

> 本文件是 augur-next 的开发计划，供新 session 快速恢复上下文。
> 最后更新：2026-06-24，当前版本 **v10.16.4**（修复 committee Kelly 仓位显示 bug，2072 tests passing，含网络测试 2077）

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

**当前能力盘点（v10.16.4）：**
- MCP 工具 13 个：analyze, consensus, committee, debate, fetch, sentiment, list_personas, configure, create_persona, workflow, **workspace_get, workspace_set, workspace_profiles**
- CLI 命令：analyze, consensus, report, serve, watch, skills, portfolio, backtest, chat, sentiment, inject-soul, telegram, slack, wechat, lark, cron-* 等
- Dashboard 19 页（含 committee, hermes-setup），委员会页已接入工作区配置
- 19 个 skill 目录（SKILL.md + manifest.json），版本号与 `augur.__version__` 自动同步
- i18n：中/英/日/韩四语言，降级链，workspace profile 9 key × 4 语言全部完整
- `augur_workflow` 默认步骤跟随终端布局预设（P2-7），定制化与 agentic 行为联动
- 投资委员会 Kelly 仓位显示已修复（v10.16.4），与 Deep Report 数字一致
- 测试基线：**2072 passed, 0 failed**（不含 5 个网络测试；含网络测试共 2077）

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

**v10.16.4：用户真机实测发现投委会 Kelly 仓位显示 bug 并修复**（见上方表格行），同时用户反馈整体产品体验问题较多（首页仪表盘点不动、投委会/深度报告多处数据不显示），判断当前还不太像可面向用户的产品形态。**这件事的优先级现在高于继续推 P2 功能 backlog**——下个 session 应该先想办法复现/定位剩余两个 UI 层问题（需要用户提供浏览器控制台报错或截图，当前环境没有浏览器自动化工具），而不是急着实现 P2-1/P2-2/P2-5/P2-6/P2-8。

**P2-3/P2-4 方法论澄清：** 用户已明确授权对 P2-3（regime 检测 hysteresis）和 P2-4（统一 OOS 校准管道）跳过"先观察再设计"的默认原则，直接设计实现——这是针对这两项的一次性授权，不代表"观察先于设计"方法论本身改变。

**下 session 待定：** 用户体验反馈的产品成熟度问题（不可点击/数据缺失）优先处理；P2-3（regime 检测加 hysteresis + 历史回测验证，已获用户授权直接设计）仍是 synthesis 文档中唯一标注的"不要把共识结果当风险输入"地基类风险，功能 backlog 内优先级最高；P1-9（dashboard router 拆分）、P2-1/P2-2/P2-4/P2-5/P2-6/P2-8 待选；用户分享了参考站点 chanlun.oldorange.club 作为产品形态参考，尚待讨论。

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
