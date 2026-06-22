# Augur v9.0.8 — 测试计划

> 供 agent 执行的完整测试 plan。
> 测试环境：`cd ~/augur && python3 -m uvicorn dashboard.app:app --port 8000`
> 跳过项：`tests/test_analyze_api_v12.py`（需要真实网络，本地跳过）

---

## 0. 前置检查

```bash
cd ~/augur
git status                          # 工作树干净
git log --oneline -3                # 确认在 f420818
python3 -m pytest tests/ -q --tb=no --ignore=tests/test_analyze_api_v12.py 2>&1 | tail -3
# 期望：1656 passed
```

---

## 1. 自动化测试套件（全量跑）

```bash
python3 -m pytest tests/ -v --tb=short \
  --ignore=tests/test_analyze_api_v12.py \
  -o "log_cli=false" \
  2>&1 | tee /tmp/augur_test_report.txt | tail -30
```

**关注点：**
- 总数必须 ≥ 1656 passed，0 failed
- 重点检查以下测试文件是否全绿：

| 文件 | 覆盖内容 |
|------|---------|
| `test_websocket.py` | /ws/analyze, /ws/committee, /ws/prices |
| `test_consensus_compare_api_v11c.py` | /api/compare, /api/committee |
| `test_cli.py` | CLI 全套命令 |
| `test_api.py` | 核心 API 端点 |
| `test_e2e_pipeline.py` | 端到端流程 |

---

## 2. 新功能专项测试

### 2.1 `/ws/committee` WebSocket 流式输出

**用 FastAPI TestClient 验证：**

```python
from fastapi.testclient import TestClient
from dashboard.app import app
client = TestClient(app)

# Case 1: 2 个大师，验证流式顺序
with client.websocket_connect("/ws/committee") as ws:
    ws.send_json({"ticker": "AAPL", "agents": ["buffett", "graham"], "question": "估值合理吗？"})
    msgs = []
    for _ in range(10):
        msg = ws.receive_json()
        msgs.append(msg)
        if msg["type"] == "verdict":
            break
    
    agent_msgs = [m for m in msgs if m["type"] == "agent"]
    verdict_msgs = [m for m in msgs if m["type"] == "verdict"]
    
    assert len(agent_msgs) == 2, f"期望 2 个 agent 消息，得到 {len(agent_msgs)}"
    assert len(verdict_msgs) == 1, "必须有且仅有 1 个 verdict 消息"
    assert verdict_msgs[-1] == msgs[-1], "verdict 必须是最后一条消息"
    
    # 验证 verdict 结构
    v = verdict_msgs[0]["verdict"]
    assert "signal" in v and v["signal"] in ("bullish", "neutral", "bearish")
    assert 0 <= v["score"] <= 10
    assert 0 <= v["confidence"] <= 1
    assert set(v["vote"].keys()) == {"bullish", "neutral", "bearish"}
    
    # 验证 opinions 按评分降序
    opinions = verdict_msgs[0]["opinions"]
    scores = [op["score"] for op in opinions]
    assert scores == sorted(scores, reverse=True), "opinions 应按评分降序"

# Case 2: 无效 ticker 返回 error
with client.websocket_connect("/ws/committee") as ws:
    ws.send_json({"ticker": "AAPL;DROP", "agents": ["buffett"], "question": "?"})
    msg = ws.receive_json()
    assert msg["type"] == "error"

# Case 3: 空 agents 列表 → 运行所有大师（至少收到第一条 agent 消息）
with client.websocket_connect("/ws/committee") as ws:
    ws.send_json({"ticker": "NVDA", "agents": [], "question": "分析"})
    msg = ws.receive_json()
    assert msg["type"] == "agent"
    ws.close()
```

**期望：** 3 个 Case 全部 assert 通过，无异常。

---

### 2.2 `augur committee` CLI 命令

```bash
# Case 1: 预设委员会
augur committee AAPL --preset value 2>&1 | head -30
# 期望：包含 "COMMITTEE" 或大师名，包含 "BUY/SELL/HOLD" 信号

# Case 2: 指定大师
augur committee NVDA --agents buffett,munger --question "护城河是否真实？" 2>&1 | head -30
# 期望：包含 Buffett 和 Munger 两位大师的意见

# Case 3: 全体委员会（耗时较长，可用 timeout）
timeout 120 augur committee TSLA --preset all 2>&1 | tail -10
# 期望：最后包含裁决结果

# Case 4: 缺少 ticker 报错
augur committee --preset value 2>&1
# 期望：显示 "Missing argument" 或帮助信息
```

---

### 2.3 `augur update` CLI 命令

```bash
# 在 git 仓库里运行
augur update 2>&1
# 期望：显示当前版本，执行 git pull，显示结果
# 如果已是最新：显示 "Already up to date" 或类似

# 在非 git 目录测试错误处理
cd /tmp && augur update 2>&1
# 期望：优雅报错，不崩溃
cd ~/augur
```

---

### 2.4 Compare 雷达图（页面级验证）

```bash
# 验证页面包含 Chart.js 和 radar canvas
curl -s http://localhost:8000/compare | grep -c "chart.js"
# 期望：1

curl -s http://localhost:8000/compare | grep -c "compare-radar-canvas"
# 期望：1

# 验证 i18n 包含雷达图 key
grep "compare-radar-title" dashboard/static/js/i18n.js | wc -l
# 期望：2（zh 和 en 各一条）
```

---

### 2.5 `/api/committee` 兼容性（旧 REST 接口不能破坏）

```bash
curl -s -X POST http://localhost:8000/api/committee \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","agents":["buffett","graham"],"question":"估值合理吗？"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('ok' if d.get('status')=='ok' else 'FAIL:', list(d.keys()))"
# 期望：ok ['status', 'ticker', 'question', 'opinions', 'verdict', ...]
```

---

## 3. 页面可访问性测试

所有页面必须返回 200，无 500 错误：

```bash
PAGES=(/ /stocks /signals /scanner /watchlist /portfolio /settings
       /personas /create-persona /history /compare /debate /committee
       /hermes-setup /performance /backtest /chat /optimizer)

for page in "${PAGES[@]}"; do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000$page)
    if [ "$code" != "200" ]; then
        echo "FAIL $page → $code"
    else
        echo "OK   $page"
    fi
done
```

**期望：** 所有页面输出 `OK`。

---

## 4. API 端点冒烟测试

```bash
# 健康检查
curl -s http://localhost:8000/health | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='ok', d"
echo "health: OK"

# Personas 列表
curl -s http://localhost:8000/api/personas | python3 -c "import json,sys; d=json.load(sys.stdin); assert len(d)>=18, f'only {len(d)} personas'"
echo "personas: OK"

# Compare（2位大师）
curl -s -X POST http://localhost:8000/api/compare \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","agent_ids":["buffett","munger"]}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['agent_count']==2"
echo "compare: OK"

# History
curl -s http://localhost:8000/api/history | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'records' in d"
echo "history: OK"

# Sentiment
curl -s http://localhost:8000/api/sentiment/AAPL | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'ticker' in d"
echo "sentiment: OK"
```

---

## 5. MCP 工具验证

```bash
# 验证 9 个工具注册正确
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | augur mcp-server 2>/dev/null \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
tools = [t['name'] for t in d.get('result', {}).get('tools', [])]
expected = [
    'mcp_augur_analyze', 'mcp_augur_consensus', 'mcp_augur_committee',
    'mcp_augur_debate', 'mcp_augur_fetch', 'mcp_augur_sentiment',
    'mcp_augur_list_personas', 'mcp_augur_configure', 'mcp_augur_create_persona'
]
missing = [t for t in expected if t not in tools]
extra   = [t for t in tools if t not in expected]
print(f'tools: {len(tools)} registered')
if missing: print('MISSING:', missing)
if extra:   print('EXTRA:', extra)
assert len(tools) == 9 and not missing, 'MCP tool count mismatch'
print('MCP: OK')
"
```

---

## 6. Skill Manifest 验证

```bash
# 所有 manifest 的命令应为 augur mcp-server
python3 -c "
import json, glob, sys
errors = []
for path in sorted(glob.glob('skills/*/manifest.json')):
    with open(path) as f:
        d = json.load(f)
    mcp = d.get('mcp', {})
    if mcp.get('command') != 'augur':
        errors.append(f'{path}: command={mcp.get(\"command\")}')
    if mcp.get('args') != ['mcp-server']:
        errors.append(f'{path}: args={mcp.get(\"args\")}')
if errors:
    print('FAIL:')
    for e in errors: print(' ', e)
    sys.exit(1)
else:
    print(f'OK: {len(glob.glob(\"skills/*/manifest.json\"))} manifests valid')
"
```

---

## 7. 回归测试（关键路径）

```bash
# 单个大师分析（不使用网络，mock 数据）
python3 -c "
from augur.registry import AgentRegistry
from augur.personas.base import MarketContext
reg = AgentRegistry()
agents = reg.get_all()
ctx = MarketContext(ticker='TEST', pe=20, roe=0.15, price=100)
result = agents[0].analyze(ctx)
assert 0 <= result.score <= 10
assert result.signal.value in ('bullish', 'neutral', 'bearish')
print(f'Agent analysis: OK ({agents[0].agent_id} → {result.signal.value} {result.score:.1f})')
"

# 共识机制
python3 -c "
from augur.registry import AgentRegistry, DecisionCoordinator
from augur.personas.base import MarketContext
reg = AgentRegistry()
coord = DecisionCoordinator(reg)
ctx = MarketContext(ticker='TEST', pe=20, roe=0.15, price=100)
agents = reg.get_all()[:3]
responses = {a.agent_id: a.analyze(ctx) for a in agents}
consensus = coord.get_consensus(responses, ticker='TEST', context=ctx)
assert 0 <= consensus.score <= 10
print(f'Consensus: OK ({consensus.signal.value} {consensus.score:.1f})')
"
```

---

## 8. 验收标准

| 检查项 | 期望 |
|--------|------|
| 全量 pytest | ≥ 1656 passed，0 failed |
| /ws/committee Case 1-3 | 全部通过 |
| CLI committee 4 个 case | 无崩溃，输出格式正确 |
| CLI update | 正常运行，优雅报错 |
| 所有页面 HTTP 200 | 19/19 |
| API 冒烟测试 | 5/5 通过 |
| MCP 工具数量 | 正好 9 个 |
| Skill manifest | 19 个全部 command=augur, args=[mcp-server] |

**若全部通过，可发 v9.0 正式版。**

---

## 10. v10.15 Agentic Workflow + Workspace 专项测试

> 新增于 v10.15：覆盖 `augur.workflow` 多步链、`/api/workspace` 预设、consensus 增强模块。

### 10.1 自动化测试

```bash
cd ~/augur
python3 -m pytest tests/test_v10_14_workspace_workflow.py tests/test_e2e_agentic_v10_15.py -v --tb=short
```

**期望：** 全部 passed（约 35+ 项），0 failed。

| 文件 | 覆盖内容 |
|------|---------|
| `test_v10_14_workspace_workflow.py` | workspace 预设/持久化、consensus 子模块、workflow 单步、Dashboard `/api/workspace` |
| `test_e2e_agentic_v10_15.py` | 完整 workflow 链（fetch→analyze→consensus→committee→debate→sentiment）、workspace 预设 round-trip、MCP 校验逻辑 |

### 10.2 Workflow API（`run_workflow`）

**用 mock 数据验证多步链：**

```python
from unittest.mock import patch
from augur.personas.base import MarketContext, AgentResponse, SignalType
from augur.registry import DecisionCoordinator
from augur.workflow import run_workflow

ctx = MarketContext(ticker="NVDA", pe=60, sector="Technology", price=500)
mock = AgentResponse(
    agent_id="buffett", agent_name="Buffett",
    signal=SignalType.BULLISH, confidence=0.8, score=7.5, reasoning="Test",
)
consensus = AgentResponse(
    agent_id="consensus", agent_name="Consensus",
    signal=SignalType.BULLISH, confidence=0.78, score=7.8, reasoning="OK",
    metadata={"position_sizing": {"position_pct": 8.5}},
)

with patch("augur.data.fetch_market_context", return_value=ctx):
    with patch.object(DecisionCoordinator, "analyze_with_all", return_value={"buffett": mock}):
        with patch.object(DecisionCoordinator, "get_consensus", return_value=consensus):
            result = run_workflow("NVDA", steps="fetch,analyze,consensus")

assert result["ticker"] == "NVDA"
assert result["results"]["consensus"]["kelly_pct"] == 8.5
assert "Consensus" in result["summary"]
```

**无效 step 应抛 ValueError：**

```python
import pytest
from augur.workflow import run_workflow
with pytest.raises(ValueError, match="Unknown step"):
    run_workflow("AAPL", steps="invalid_step")
```

### 10.3 Workspace 预设 API

```python
from fastapi.testclient import TestClient
from dashboard.app import app
client = TestClient(app)

# 列出预设
r = client.get("/api/workspace/presets")
assert r.status_code == 200
assert "trader" in r.json()["presets"]

# 应用 trader 预设（需显式传 default_page，否则 Pydantic 默认 "/"）
r = client.put("/api/workspace", json={
    "layout_preset": "trader",
    "default_page": "/stocks",
})
assert r.json()["workspace"]["default_page"] == "/stocks"
assert "backtest" in r.json()["workspace"]["hidden_nav"]

# committee 预设
r = client.put("/api/workspace", json={
    "layout_preset": "committee",
    "default_page": "/committee",
    "show_ticker_tape": False,
})
assert r.json()["workspace"]["default_page"] == "/committee"
assert r.json()["workspace"]["show_ticker_tape"] is False
```

### 10.4 Consensus 模块（mock 数据）

```python
from augur.consensus.industry_matrix import get_agent_weights
from augur.consensus.regime_weights import apply_regime_weights
from augur.consensus.probability_calibrator import calibrate_confidence

w = get_agent_weights("technology", {})
assert sum(w.values()) == pytest.approx(1.0, abs=0.01)

adj = apply_regime_weights({"buffett": 0.5, "marks": 0.5}, "BEAR_LOW_VOL")
assert sum(adj.values()) == pytest.approx(1.0, abs=0.01)

c = calibrate_confidence(8.0, 0.7, "consensus")
assert 0.05 <= c <= 0.95
```

### 10.5 MCP `augur_workflow` 校验

无需启动 MCP server，验证 ticker 校验与 workflow 错误路径：

```python
from augur.mcp_server import _validate_ticker
assert _validate_ticker("NVDA;DROP") is not None
assert _validate_ticker("AAPL") is None
```

### 10.6 验收标准（v10.15）

| 检查项 | 期望 |
|--------|------|
| `test_v10_14_workspace_workflow.py` | 全部 passed |
| `test_e2e_agentic_v10_15.py` | 全部 passed |
| workflow 多步链 | fetch/analyze/consensus/committee/debate/sentiment 结构正确 |
| workspace 四预设 | analyst/trader/committee/minimal API round-trip |
| consensus 模块 | industry_matrix、regime_weights、probability_calibrator 边界正确 |

---

## 9. 测试报告模板

```
日期：____
测试人：____
环境：Python ____ / augur v9.0.8

pytest 结果：____ passed / ____ failed
WS committee：通过 / 失败（描述）
CLI committee：通过 / 失败（描述）
CLI update：通过 / 失败（描述）
页面可访问：____/19
API 冒烟：____/5
MCP 工具：____/9
Manifest：____/19

总体结论：通过 / 不通过
需要修复：____
```
