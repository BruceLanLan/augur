# Contributing to Augur

感谢你对 Augur 的关注！以下是贡献指南。

---

## 贡献方式

### 1. 新增投资人 Persona

**方式 A：YAML（无代码，推荐快速实验）**

```yaml
# personas/custom/my_persona.yaml
agent_id: my_quant
name: "我的量化策略"
philosophy: ["价值", "动量"]
scoring_weights:
  value: 0.60
  momentum: 0.40
factors:
  value:
    base: 5
    rules:
      - {if: "pe > 0 and pe < 15", add: 3}
      - {if: "pb < 1.5 and pb > 0", add: 2}
  momentum:
    base: 5
    rules:
      - {if: "rsi > 50 and rsi < 70", add: 2}
      - {if: "macd > macd_signal", add: 1}
```

保存后立即生效（`augur list-personas` 可见）。

**方式 B：Python（完整控制）**

参考 `src/augur/personas/buffett.py`，继承 `BaseAgent` 并实现 `analyze(ctx)` 方法。

规范：
- `agent_id`：小写字母+下划线
- `analyze()` 必须返回 `AgentResponse`，`score` 范围 0-10
- `scoring_weights` 之和应为 1.0
- `coverage_confidence`：当框架不适用时降低权重（0-1）
- 添加对应的 `skills/{agent_id}/SKILL.md`

### 2. 修复 Bug

1. 先确认 Bug 可复现（提供最小复现步骤）
2. 修改代码，运行全量测试：
   ```bash
   cd augur
   python3 -c "
   import sys; sys.path.insert(0,'src')
   from augur.coordinator import DecisionCoordinator
   from augur.personas.base import MarketContext
   coord = DecisionCoordinator()
   ctx = MarketContext(ticker='TEST', pe=25, gross_margins=0.45, roe=0.20)
   results = coord.analyze_with_all(ctx)
   print(f'{len(results)} personas passed')
   "
   ```
3. 提交 PR，描述中说明：问题原因、修复方案、影响范围

### 3. 改进 Dashboard

- 模板在 `dashboard/templates/`，CSS 在 `dashboard/static/css/bloomberg.css`
- JS 单位约定：市值/FCF 用**十亿 USD**，比率/利润率用**小数**（0.46 = 46%）
- 启动本地开发服务器：`python3 -m dashboard.app --port 8000 --reload`

### 4. 改进文档

- README.md（中文）和 README_EN.md（英文）需保持同步
- CLI 命令示例必须实际可执行
- 数值示例使用正确单位（见参数约定）

---

## 参数约定（必须遵守）

| 类型 | 单位 | 示例 |
|------|------|------|
| 利润率 / 增速 / 比率 | 小数 | `roe=0.55`（55%），`debt_ratio=0.35`（35%） |
| 持仓比例 | 整数百分比 | `institutional_ownership=66`（66%） |
| 市值 / FCF | 十亿 USD | `market_cap=2800`（$2.8T），`fcf=90`（$90B） |
| RSI | 直接数值 | `rsi=55` |

---

## 代码风格

- Python：无格式化工具强制要求，但保持与现有代码一致
- 变量名：snake_case
- 注释：代码逻辑清晰时不写注释，只在"为什么"不明显时才写
- 不要引入新的必须依赖（可放入 optional extras）

---

## PR 流程

1. Fork → 创建分支（`fix/xxx` 或 `feat/xxx`）
2. 修改代码 + 通过全量测试
3. 提交 PR，标题格式：`fix: ...` / `feat: ...` / `docs: ...`
4. PR 描述中包含：问题背景、改动说明、测试方法

---

如有问题，欢迎在 [Issues](https://github.com/BruceLanLan/augur/issues) 讨论。
