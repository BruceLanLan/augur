# Augur 第二轮审查报告（Pass-2）

**日期：** 2026-06-02  
**范围：** 5 个并行子 agent（各 10 轮，共 50 轮迭代）+ 收尾验证  
**基线分支：** `feature/phase-a-real-data`  
**收尾分支：** `feature/review-pass-2`

---

## 执行摘要

Pass-2 在首轮修复（learning、registry、data）之上，对后端核心、Dashboard UX/i18n、API 安全、测试套件进行了系统化加固。五个子 agent 中 **四个完成并返回摘要**；**a11y/i18n 专用 agent 在约 10 分钟轮询后仍未写入完成摘要**（transcript 仅 1 行），但工作区已包含 signals 等页面的 i18n/a11y 相关 diff（可能来自并行改动或未完成会话）。

收尾阶段在 `HOME=$PWD/.pytest-home` 下运行全量 pytest：**675 passed**，无阻塞失败，无需额外修复。

**变更规模：** 46 个文件，约 +2493 / -627 行（不含 `.pytest-home` 测试缓存）。

---

## 按领域划分的优化

### 1. 后端核心（`src/augur/`，Agent: backend）

| 轮次 | 发现 | 修复 |
|------|------|------|
| 1 | `ref_date` 未使用；循环内 import | 模块级 import；删除死代码 |
| 2 | 共识默认权重用 `1/len(results)`，含 ERROR agent | `valid_count` 仅统计非 ERROR |
| 3 | Ruff F401/F841 | 清理 chat、history、optimizer、plugins、registry 等未使用符号 |
| 4 | 历史文件名可含非法 ticker 字符 | `_safe_ticker_label()` 消毒 |
| 5 | 批量拉取 ticker 映射 O(n²) | `norm_to_origs` 别名映射 |
| 6 | `debate_summary` 构建未使用 | 辩论 findings 加入摘要头 |
| 7 | `asyncio.Lock` 可能绑错事件循环 | 运行循环变化时重建锁 |
| 8 | `authenticate()` 接受畸形用户名 | 登录用户名正则校验 |
| 9 | `min_age_days` 结果解析无上限年龄 | 超过 `lookback + min_age` 的预测跳过 |
| 10 | Graham 信号用 `avg_score` 而非加权 `total_score` | 信号改由 `total_score` 驱动 |

**涉及文件：** `auth.py`, `backtest.py`, `chat.py`, `data.py`, `history.py`, `learning.py`, `optimizer.py`, `persona_loader.py`, `personas/graham.py`, `plugins.py`, `registry.py`, `sentiment.py`, `streaming.py`, `users.py`

**关键代码（共识权重）：**

```python
valid_count = sum(
    1 for r in results.values() if r.signal != SignalType.ERROR
)
default_weight = 1.0 / valid_count if valid_count else 1.0
```

**关键代码（历史路径安全）：**

```python
def _safe_ticker_label(ticker: str) -> str:
    label = (ticker or "").strip().upper()
    # 仅保留字母数字与有限分隔符 ...
```

---

### 2. Dashboard UX / i18n（Agent: dashboard UX）

十个 UX 循环聚焦 **index / settings / scanner / portfolio**：

1. Index 欢迎横幅 `data-i18n`
2. Hero 区（示例、快捷键、进度、信号标签、CTA、错误面板）
3. 市场面板（刷新、国际/商品/涨跌榜、广度说明）
4. Index JS 动态文案统一 `_t()`
5. Settings 静态区块 A–E
6. Settings JS（API key 占位符不再硬编码「已配置」）
7. Scanner 空闲 `empty-state`
8. Scanner 错误/进度 toast i18n
9. Portfolio 全页 i18n
10. Portfolio 空状态升级（图标 + CTA；空时隐藏 summary/分析区）

**约 80+ 新 zh/en 键**（`dashboard/static/js/i18n.js`）。

**未覆盖：** Settings toast/confirm、performance 页 JS、index 宏观评论文案仍部分硬编码。

---

### 3. API / 认证 / WebSocket（Agent: API security）

| 缺口 | 修复 |
|------|------|
| JWT 登录后 `/api/*` 未强制 | `auth.py` 统一 `authenticate_bearer`；中间件接受 API token **或** JWT |
| `augur-token` vs `augur_api_token` 不一致 | `base.html`、`chat.html` 双源 Bearer |
| 无 JWT 身份端点 | `GET /api/auth/me` |
| `/api/auth/verify` 仅 API token | 返回 `mode: open \| token \| jwt` |
| WS 绕过 HTTP 中间件 | `authenticate_websocket()` + `?token=` 查询参数 |
| 登录暴力破解 | **10 次/分钟/IP**（`check_auth_rate_limit`） |
| IP 限流文档错误 | `docs/api-reference.md` 更正；响应头 `X-RateLimit-Remaining` |

**WebSocket 鉴权要点：**

```python
def get_websocket_token(websocket) -> Optional[str]:
    token = extract_bearer_token(websocket.headers.get("authorization", ""))
    if token:
        return token
    query_token = websocket.query_params.get("token")
    ...
```

**定向测试：** 72 passed（auth、websocket、users、chat、market_endpoints、edge_cases_v8）。

---

### 4. 测试与回归（Agent: tests）

- **10 轮循环：** 9/10 全绿（第 4 轮 `test_record_outcome_min_age_days` 一度 flaky）
- **修复：** 固定 epoch + `patch("augur.learning.time.time")`；pipeline perf 预热 + 阈值 5s→10s
- **新增/强化回归（净 +11，664→675）：**
  - `test_learning.py`：`min_age_days`、`too_stale_skipped`
  - `test_registry.py`：全 ERROR → NEUTRAL；空 registry 不崩
  - `test_data.py`：无效 ticker → `[]`
  - `test_optimizer.py`：`n_points=1` 无除零
  - `test_plugins.py`：激活失败、单次 load
  - `test_rules.py`：多条件 AND、畸形 YAML
  - `test_sentiment.py`：空/空白 ticker
  - `test_auth.py`：JWT + WS（约 6 项）
  - `test_integration_v8.py`：共识情绪因子补丁断言加强

---

### 5. a11y / 响应式 / 全站 i18n（Agent: a11y — **未完成摘要**）

专用 agent 未返回完成摘要。工作区仍包含：

- `dashboard/templates/signals.html` — 大量 `data-i18n` / 结构整理
- `dashboard/static/css/ui-enhance.css` — 焦点环、`prefers-reduced-motion`、触控目标、响应式断点
- `dashboard/i18n/en.json`、`zh.json` — 与 `i18n.js` 同步扩展
- 多模板（compare、debate、history、login、watchlist 等）辅助 a11y 属性

**建议：** 下一轮单独完成 a11y agent 的 10 轮并补全 signals/performance 的键盘导航审计。

---

## 变更文件清单

### 后端
- `src/augur/auth.py`, `backtest.py`, `chat.py`, `data.py`, `history.py`, `learning.py`, `optimizer.py`, `persona_loader.py`, `personas/graham.py`, `plugins.py`, `registry.py`, `sentiment.py`, `streaming.py`, `users.py`

### Dashboard
- `dashboard/app.py`
- `dashboard/i18n/en.json`, `zh.json`
- `dashboard/static/js/i18n.js`, `static/css/ui-enhance.css`
- `dashboard/templates/base.html`, `chat.html`, `compare.html`, `debate.html`, `history.html`, `index.html`, `login.html`, `performance.html`, `portfolio.html`, `register.html`, `report_view.html`, `scanner.html`, `settings.html`, `signals.html`, `stocks.html`, `watchlist.html`

### 文档
- `docs/api-reference.md`
- `docs/REVIEW_PASS2_REPORT.md`（本文件）

### 测试
- `tests/test_auth.py`, `test_data.py`, `test_data_pipeline.py`, `test_integration_v8.py`, `test_learning.py`, `test_optimizer.py`, `tests/test_plugins.py`, `test_registry.py`, `test_rules.py`, `test_sentiment.py`

**未纳入提交：** `.pytest-home/`, `.pytest-tmp-home/`（本地测试 HOME 与缓存）

---

## 测试结果

```bash
HOME=$PWD/.pytest-home .venv/bin/pytest -q --tb=line
# 675 passed in ~15s
```

子 agent 报告：backend 674→675；API 定向 72；tests 三轮确认均为 675/675。

---

## 待办（Backlog）

1. **完成 a11y agent 10 轮**并补 transcript；审计 signals/performance 键盘与 ARIA。
2. Settings **toast/confirm**、performance **JS 字符串**、index **宏观评论** 全面 i18n。
3. **E2E / Playwright** 覆盖 JWT 登录 + WS `?token=` 浏览器路径。
4. **Rate limit** 可考虑 Redis/共享存储（多实例部署）。
5. **Chat 页** 其余 fetch 路径与流式端点一致性复查。
6. **文档：** OpenAPI 与 `api-reference.md` 自动生成同步。
7. **CI：** 固定 `HOME=$PWD/.pytest-home` 或文档化隔离目录。
8. **共识权重：** 空 registry / 全 ERROR 的 UX 提示（Dashboard 层）。
9. **Learning：** 自动 outcome 与 yfinance 失败时的可观测指标。
10. **合并策略：** `feature/review-pass-2` → `main` 前需与 `feature/phase-a-real-data` 协调冲突。

---

## 子 Agent 完成状态

| Agent | ID（transcript） | 状态 |
|-------|------------------|------|
| Backend | `e6355baa-…` | ✅ 完成 |
| Dashboard UX | `c9e088fc-…` | ✅ 完成 |
| API security | `8e82f50f-…` | ✅ 完成 |
| Tests | `7c4fc081-…` | ✅ 完成（9/10 轮后修复至 675） |
| a11y/i18n | `d48b1b68-…` | ⚠️ 超时/无完成摘要 |

---

*报告由 Pass-2 finalizer 生成。*
