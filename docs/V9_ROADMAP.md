# Augur Next v9 — 开发路线图

> 本文件是 augur-next 的开发计划，供新 session 快速恢复上下文。
> 最后更新：2026-06-08，当前版本 **v9.0.8**

---

## 总目标

把 Augur 打造成**专业的 Bloomberg AI Agent 系统**：
- 18 位投资人风格的独立 Agent
- 易于任何人接入（网页版 / Agent 版 / CLI）
- 及时更新、用户可高度 DIY
- 接入 OpenClaw / Hermes Agent 等
- 编程成一个独立 App

**仓库分工：**
- `augur`（github.com/BruceLanLan/augur）= 稳定版，当前 **v8.2.3**
- `augur-next`（github.com/BruceLanLan/augur-next）= 开发版，当前 **v9.0.8**
- 本地：`feature/v9-dev` 分支跟踪 augur-next/main
- 推送命令：`git push augur-next feature/v9-dev:main`

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
| 9.0.8 | `augur committee` CLI 命令 + `augur update` 自更新 + compare 雷达图 |

**当前能力盘点：**
- MCP 工具 9 个：analyze, consensus, committee, debate, fetch, sentiment, list_personas, configure, create_persona
- CLI 命令：analyze, consensus, report, serve, watch, skills, portfolio, backtest, chat, sentiment, inject-soul, telegram, slack, wechat, lark, cron-* 等
- Dashboard 19 页（含 committee, hermes-setup）
- 19 个 skill 目录（SKILL.md + manifest.json）
- 测试基线：**1652 passed**（排除网络测试 test_analyze_api_v12.py）

---

## 待办（下个 session 从这里开始）

### P1 — 核心增强（已完成 3/5）

3. **委员会流式输出**（committee.html）
   - 现在是一次性返回，改成逐个大师意见流式展示（WebSocket 或轮询）
   - 参考现有 `/ws/analyze/{ticker}` WebSocket 模式

### P2 — 生态扩展

6. **OpenClaw 实测接入文档**
   - 实际在 OpenClaw 里测试 augur-mcp，写真实接入步骤
   - docs/openclaw-setup-guide.md

7. **PyPI 发布准备**
   - `augur-agents` 包发布到 PyPI，让 `pip install augur-agents` 直接可用
   - 检查 pyproject.toml 的 classifiers、long_description
   - GitHub Actions 自动发布 workflow

8. **Electron/Tauri 桌面 App 封装**（"独立 app"终极形态）
   - 把 Dashboard 封装成桌面应用
   - 或先用 PWA（已完成）作为轻量方案

### P3 — 打磨

9. **README 截图更新** — 委员会页、hermes-setup 页的实际截图
10. **E2E Playwright 测试** — 关键用户流程
11. **多语言扩展** — 日语/韩语 i18n（面向亚洲市场）

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
git log --oneline -5              # 确认在 v9.0.8
git status                        # 确认工作树干净
python3 -m pytest tests/ -q --tb=no --ignore=tests/test_analyze_api_v12.py 2>&1 | tail -3
```
