# augur-next 评审报告（2026-09-03，Fable 5.1）

**评审对象**：`origin/main` @ `df60456`（v11.0.0-rc1，DSH 多 agent 循环 2026-08-11～08-13 产出，144 个 commit、+42k 行）
**评审方式**：从零重建环境（python 3.12 + uv）、全量测试、CI 日志回溯、Dashboard 起服探测、对一份真实使用中的数据目录做只读取证
**结论先行**：v11 的代码主体是健康的（本地全量 3422 通过），但**围绕它的证据链是坏的**——CI 的「Tests」自 8/12 起每次都是假绿（0 个测试真正跑过），「Hermetic Smoke」自创建起全红，README 状态表据此写的「全绿」不成立。另外发现一个会实际改变用户结果的缺口：R6 学习权重在没有任何验证门槛的情况下以 40% 混入共识，而 v11 自己的原则 2 明令禁止。本轮把这几项都修了，并把后续规划写进 [`docs/ROADMAP.md`](../ROADMAP.md)。

每条 finding 标注证据等级：**[实测]** 本次亲自复现；**[日志]** 来自 CI/生产日志；**[推断]** 有证据但未直接复现。

---

## 一、本轮修复（已随本 commit 落地）

### F1 · CI「Tests」工作流是假绿 — P0 [日志+实测]

- **现象**：8/12 之后 `Tests` 每次 push 都 success，但三个矩阵 job 各只跑 30～45 秒；v10 时代同一工作流跑 2461 个测试需要 4m43s。
- **根因**：`tests.yml` 里 `python -m pytest ... 2>&1 | tail -20`。GitHub Actions 默认 shell 是 `bash -e`，**没有 `pipefail`**，步骤退出码是 `tail` 的 0。这条管道 6 月（`e3caead`）就在，只是当时测试能跑；8/12 起 `src/augur/capability.py` 顶层 `import jsonschema` 而 `jsonschema` 不在任何依赖组里，pytest 在收集阶段中断（`ModuleNotFoundError: No module named 'jsonschema'` … `1 error in 7.56s`），于是变成「0 个测试 + 绿灯」。
- **修复**：`set -o pipefail`、去掉 `tail`、pytest 作为步骤最后一条命令；新增「Assert tests actually ran」步骤，收集数 < 3000 视为失败；`jsonschema>=4.0` 进核心依赖（`capability.py` 被 `skills/permissions.py`、`schemas/skill_spec.py` 引用，是产品路径）。
- **验证点**：下一次 push 三个矩阵 job 必须各自出现真实的 `N passed` 行，且耗时回到分钟级。py3.9 job 一个月来第一次真正跑 42k 新代码，可能暴露新问题——见 ROADMAP 步骤 0。

### F2 · CI「Hermetic Smoke」自创建起全红 — P0 [日志]

- **现象**：`hermetic-smoke.yml`（`058c3cb`，8/12 创建）的 wheel/sdist 两个 job 每次都失败在 `ruff check` 步：`ruff: command not found`。
- **根因**：ruff 装进了 `/tmp/augur_venv_*/bin/`，却裸调用 `ruff`；runner 上没有全局 ruff。另外 pip-audit 步骤「装不上就跳过」和「跑不了就失败」互相矛盾。
- **修复**：改为调用 venv 内的 `ruff`；工具缺失即失败（这正是 ROADMAP Day 2 的门禁要求）；ruff 钉 `>=0.16,<0.17`；pip-audit 统一为硬失败。本地 `pip-audit --local`：**无已知漏洞**。

### F3 · R6 学习权重无门槛混入共识 — P0 [实测]

- **现象**：`src/augur/consensus/engine.py` 对 rolling-IC 权重有 C1.2 校准门（非 `validated-calibrated` 不混入，`AUGUR_FORCE_RIC=1` 可强制），但紧接着的 v8 学习权重分支只看 `LearningEngine.has_learned_weights`——该属性在**任一 agent 有 ≥3 个 resolved outcome** 时即为真，对 ticker 数、窗口独立性零要求。
- **真实数据取证**（一份持续运行的定时分析所积累的 `learned_weights.json`，只读查看）：
  - resolved 288 条 = 18 agents × 16 次运行，**全部来自同一只股票**，16 个 30 天窗口彼此重叠。
  - 由此得到的权重最低 0.027、最高 0.097，3.6 倍分布；某些大师 0/16、另一些 14/16，本质是「过去一个月谁看多这只票」，不是能力差异。
  - 只要 `has_learned_weights` 为真，这份数据就会以 60/40 混入每一次共识计算。
- **判断**：违反 ROADMAP 原则 2（任何动态权重必须过预注册 OOS gate）；rolling-IC 的门 v11 做了，学习权重的门漏了。
- **修复**：学习权重混入改为 opt-in（`AUGUR_FORCE_LEARNED=1`），默认跳过并记 info 日志，与 `AUGUR_FORCE_RIC` 对称；新增 `tests/test_learned_weight_gate.py` 两条测试（默认与冷启动共识相等；opt-in 后共识改变）。**真正的门怎么设计是 owner 决策**（见 ROADMAP 步骤 3）。

### F4 · `mcp` 2.x 破坏 MCP server — P1 [实测]

- `pyproject` 写的是 `mcp>=1.0.0` 无上界；今天 fresh install 拿到 mcp 2.1.1，`mcp.server.fastmcp` 已被移除，`create_server()` 直接 `ImportError`。本地全量测试唯一的失败就是它。
- 顺带发现 `tests/test_mcp_new_resources.py::test_thesis_resource_missing` 从 `augur.mcp_server` import 一个从未存在的模块级符号 `get_thesis_resource`（它是 `create_server()` 内的闭包）——这条测试在 CI 里从未真正跑过（F1）。
- **修复**：`mcp>=1.0.0,<2`；移除 `fastmcp` extra（源码零引用，纯增加解析冲突面）；测试改为通过 `mcp.read_resource("augur://thesis/…")` 走真实注册路径。mcp 2.x 迁移列入 ROADMAP。

### F5 · ruff 规则集没固定 — P1 [实测]

- `pyproject` 只写了 `ignore = ["E402"]` 没写 `select`。ruff 0.16.5 的默认规则集比以前宽，同一棵树报 **2545** 条（FA100/UP006/BLE001…）；用历史默认 `E4,E7,E9,F` 则 0 条。README 的「222 → 0」在当时是真的，但只要 CI 装到新 ruff 就会翻红。
- **修复**：显式 `select = ["E4","E7","E9","F"]`。本地 `ruff check src/` → `All checks passed!`。

### F6 · `pydantic` 是隐式依赖 — P1 [实测]

- 20 个源文件 import pydantic，但只靠 fastapi 传递安装。加入核心依赖 `pydantic>=2.0`。

### F12 · `inject_soul` 在路径穿越检查之前就 mkdir — P1 [日志+实测]（CI 复活后第一轮抓到）

- F1 修完后 CI 第一次真正跑测试（py3.11：3418 通过、1 失败），失败的是 `test_iteration5.py::TestSoulSecurity::test_path_traversal_blocked`：`PermissionError: /tmp/…/../../etc/evil`。
- **根因**：`soul.py` hermes 分支先 `profile_dir.mkdir(parents=True)` 再做 `is_relative_to` 检查，穿越尝试在被拒绝**之前**已经在输出目录外建了目录。Linux runner 上撞到 `/etc` 才报错；macOS 的 tmpdir 在 `/var/folders/...` 下可写，本地测试一直「通过」。这正是 F1 所说「假绿一个月」的代价：一个安全守卫的顺序错误被 CI 假绿盖住了。
- **修复**：mkdir 移到检查之后（检查后本来就有一次 mkdir）；新增 `test_path_traversal_creates_nothing_outside_output_dir`，已确认对旧代码失败、对新代码通过。
- 同一轮 Hermetic Smoke 的 pip-audit 报 runner venv 自带的 pip 25.0.1 有 7 条 advisory，改为审计前先升级 pip。

---

## 二、发现但未动手（owner 决策或后续阶段）

### F7 · 定时分析任务的数据质量 — P1 [实测]

- 对一个持续运行了一个多月的 `augur cron-run` 定时任务做日志取证：34 次运行里 **23 次 yfinance 取数失败**（`SSL_connect … Connection closed abruptly`），stooq 全部 404，`AUGUR_EDGAR_CONTACT_EMAIL` 未设置。同期 GitHub runner 上的每周数据源烟测全绿，说明失败来自运行环境的网络/代理，而不是数据源本身。
- 空上下文不记录预测的守卫是生效的，但代价是一个月里 R6 只攒到 9 次有效运行。
- 评审期间重建虚拟环境时，定时任务调度器在可执行文件重新出现后立即补跑了一次 `cron-run`（exit 0，只 resolve 了已有 outcome，因数据源失败未记录新预测）。**教训**：给定时任务所用的虚拟环境重建或升级，等同于部署新版本，应先确认再动。
- **建议**（ROADMAP 步骤 6）：定时任务环境不要继承交互 shell 的代理设置、设置 EDGAR 联系邮箱、watchlist 扩到回放宇宙的 37 只票；否则 R6 永远等不到能过门的数据。

### F8 · 公开仓 `augur` 的每周数据源烟测被手动关闭 — P2 [日志]

- `gh workflow list --repo BruceLanLan/augur`：`Data Source Smoke Test  disabled_manually`，最后一次运行 8/10。这是唯一一条「在生产环境里真的在工作」的证据流，现在断了。不知道是谁、为什么关的，**没有重新启用**——需要 owner 确认。
- 公开仓仍在 `eade71a`（v10.15.0 + B3），v11 从未同步；本地/私有仓领先 150 个 commit。按 ROADMAP 架构，只有 owner 批准的精确 commit 才能推过去，本轮**没有碰 `augur` remote**。

### F9 · 9 个模块没有任何产品入口 — P2 [实测]

用纯文本 grep 全 `src/`（排除自身与 egg-info），以下模块**零引用**，只有测试文件用到：

`citation_queue`、`cost_budget`、`eval_lab`、`outcome_tracker`、`pack_digest`、`prompt_eval`、`review_comment`、`risk_review`、`team_audit`

另有 `capability`、`skill_spec`、`debate_engine` 仅被其他库模块引用，用户从 CLI/Dashboard/MCP 都到不了。它们有测试、有 CHANGELOG 条目，但对用户不存在。三天写 24 个模块的代价就是这个。建议冻结新模块，先给现有模块接线或明确标 experimental（ROADMAP 步骤 4）。

### F10 · 文档与现实的偏差 — P2 [实测]

- README 状态表「3422 tests 全绿 · ruff 全绿 · wheel/sdist smoke 已验证」——本地为真，CI 为假（F1/F2）。本轮已改写为可核验的表述。
- git tag 停在 `v10.13.0`：v10.14.0、v10.15.0、v11.0.0-rc1 都没打 tag；`publish.yml` 靠 `v*` tag 触发且依赖 PyPI Trusted Publisher（尚未配置，`pypi.org/pypi/augur-agents` 404）。
- 用户级 site-packages 里残留的旧 editable 安装会让 `import augur` 解析到别的 checkout。开发时应始终在项目自己的虚拟环境里运行（README 开发指南已改为这种写法）。

### F11 · 通过项（值得记录的正面证据） [实测]

- 全量测试（修复后）：见 CHANGELOG 数字，来自真实运行。
- Dashboard 用临时数据目录起服：`/`、`/thesis`、`/scorecard`、`/earnings`、`/valuation`、`/inbox`、`/compare` 全部 200；头像 `/docs/images/avatars/*.png` 200（v10.15 那次 404 没有复发）；`/api/health`、`/api/personas`、`/api/coverage/health`、`/api/providers/health` 200。
- `scripts/deployment_check.py` PASS；`augur --help` 40 个子命令；`import augur.mcp_server` / `import dashboard.app` 正常。
- `/api/*` 鉴权是全局中间件（`api_token_auth_middleware`），配置了 token 后 45 个写接口统一受保护，不存在漏网的单个路由。

---

## 三、给后续开发的判断

1. **先修证据链，再谈发布。** v11 的「RC」目前只有本地证据。F1/F2 修完后至少看一周真绿的 CI，才有资格谈 GA。
2. **不要再增加模块。** 24 个新模块里 9 个用户到不了；下一阶段的产出应该是「用户能从 fresh install 十分钟内走通一条链路」（ROADMAP 北极星），而不是第 25 个模块。
3. **R6 的数据问题比算法问题大。** 一只票、9 次有效运行，任何权重学习都是噪声。先把定时任务的取数修好、watchlist 扩到 37 只，攒 60～90 天，再用 v11 自带的 `oos_harness` 做门。
4. **DSH 这种产出模式要配一个「真跑一遍」的关卡。** 这次所有假象（假绿 CI、导入不存在符号的测试、0→2545 的 lint）都是「本地说过了」但没人从零安装再验证一次。ROADMAP 步骤 0 把这个关卡写死。

详细分步计划见 [`docs/ROADMAP.md`](../ROADMAP.md) 的「2026-09 阶段」。
