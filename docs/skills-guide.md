# Augur Skill 使用指南 (v11)

Skill 是声明式的研究 SOP（标准操作流程）。Skill 清单本身不包含可执行代码——它声明需要哪些能力（capability）、允许访问哪些网络域名和本地资源、工作流由哪几步组成、输出必须包含什么。执行由 Augur 内置的 Skill 执行器完成。

> **当前实现状态（2026-09-17）**：4 个内置 Skill 均可端到端执行（`augur skill run`，或 MCP 工具 `augur_run_skill`）。执行器只运行内置 Skill，不加载第三方清单；步骤按依赖顺序串行执行，不做重试和并行。

## 快速上手

```bash
augur skill list                                   # 列出内置 Skill 与步骤
augur skill show filing-delta                      # 输入、能力、权限、每步访问的域名
augur skill run earnings-prep AAPL                 # 执行并打印结果摘要
augur skill run debt-covenant-review AAPL --set debt_ebitda_max=3.0
augur skill run filing-delta AAPL --json           # 完整结果（输出、步骤状态、审计记录）
```

每次执行都会保存一份 RunBundle（与 `augur workflow` 相同的格式），命令末尾会打印 Run ID，可以继续：

```bash
augur export AAPL --run-id <RUN_ID> --format evidence-pack -o pack.zip
augur verify-pack pack.zip
```

需要设置 `AUGUR_EDGAR_CONTACT_EMAIL`（SEC 要求请求带联系邮箱）。

## 内置 Skills

| Skill | 做什么 | 数据来源 | 主要输出 |
|---|---|---|---|
| `earnings-prep` | 财报前研究包：18 位大师分析 + 共识 + 基于证据的分歧图 + 与上次分析的变化 | yfinance、SEC EDGAR、本地财报日历 | `dossier` |
| `filing-delta` | 最近两份 10-K 年度数据的实质性变化（≥5% 视为重大） | SEC XBRL company facts | `delta_report` |
| `debt-covenant-review` | 杠杆（Debt/EBITDA）与利息覆盖率检查 | SEC XBRL company facts | `covenant_report` |
| `insider-cluster-review` | 近 90 天公开市场 Form 4 交易与内部人集群检测 | SEC Form 4 | `cluster_report` |

所有 Skill 的输出都包含 `run_id` 和 `evidence_manifest`（本次执行引用的证据 ID 列表）。

### `earnings-prep`

- **输入**：`ticker`（必填）；`as_of`（默认今天）、`event_id`（默认 `<TICKER>_next`）。
- **步骤**：`collect`（实时数据与证据 + 本地财报日历）→ `analyze`（全部大师 + 共识）→ `compare`（与最近一次含大师分析的运行比较）→ `synthesize`（生成 dossier）。
- **权限**：资源 `evidence.read`、`runs.read`；网络 `sec.gov`、`finance.yahoo.com`、`stooq.com`（行情备用源）。
- **限制**：下一次财报日期读取本地文件 `<数据目录>/earnings_calendar.json`，没有条目时 dossier 会明确写出"日历中无记录"，不会猜测日期。

### `filing-delta`

- **输入**：`ticker`。默认比较最近两个 10-K 财年，不需要手填 accession 号。
- **步骤**：`fetch_filings`（读取年度报表数据）→ `delta_report`（`FilingDeltaBuilder` 对比）。
- **限制**：只比较 XBRL 中的数字字段（营收、利润、利润率、负债、现金流等），不比较正文文字；季度报告（10-Q）暂不支持。文字层面的风险因素变化请用 `augur risk-review`。

### `debt-covenant-review`

- **输入**：`ticker`；可选 `debt_ebitda_max`（默认 3.5）、`interest_coverage_min`（默认 2.5）。
- **重要**：默认阈值是**参考值，不是公司信贷协议中的实际条款**（协议文本无法机器读取）。输出中 `thresholds_are_reference` 会标明是否使用了参考值。
- **限制**：公司在 XBRL 中未单独披露的项目（例如 Apple 近年不单独披露利息支出）不会被估算，会列在 `unavailable_inputs` 中并跳过相应检查。

### `insider-cluster-review`

- **输入**：`ticker`。
- **判断口径**：两位及以上内部人在窗口期内同向交易才算"集群"；只有一位内部人交易时，评估为 `no_activity`，摘要会注明"有交易但不构成集群"。

## 安全模型

### 清单校验（加载时）

所有 Skill 必须通过 `validate_skill_spec()`，v1 **严格禁止**：

- `module_path`、`import`、`shell`、`exec`、`eval`
- 任意文件路径
- Python 表达式求值

### 执行前预检（任何步骤运行之前）

执行器在第一个步骤运行**之前**检查整个工作流，任何一项不通过都会直接拒绝，不会有步骤被执行：

1. 每一步使用的能力必须在 `required_capabilities` 中声明；
2. 该能力必须已注册且有真实实现（未实现 → `SkillNotRunnable`）；
3. 该能力会访问的每个网络域名必须在 `permissions.network_domains` 中；
4. 该能力会读取的每类本地资源必须在 `permissions.resources` 中。

> 预检依据的是每个能力**声明**会访问的域名和资源（见下表，与代码中的数据源链保持一致并有测试约束），它是执行前的权限关卡，不是运行时网络沙箱：能力内部调用的库本身不受拦截。

允许和拒绝的检查都会写入审计记录，保存在 RunBundle 的 `metadata.skill.audit_log` 中；执行结果同时写入 `augur audit` 可查看的审计日志。

```python
from augur.skills.runner import SkillRunner, get_builtin_skill

runner = SkillRunner(get_builtin_skill("filing-delta"))
result = runner.run({"ticker": "AAPL"})
print(result.status, result.run_id)
print(result.audit_log[:3])   # ["ALLOWED capability 'sec.financials.annual' for step 'fetch_filings'", ...]
```

### 能力列表

`augur skill show <id>` 会显示每一步的能力说明和网络访问。当前注册的能力：

| 能力 | 实现 | 网络 |
|---|---|---|
| `earnings.collect_evidence` | `fetch_market_context` + 本地财报日历 | finance.yahoo.com、stooq.com、sec.gov |
| `personas.analyze` | 全部大师分析 + 加权共识 | finance.yahoo.com（VIX/SPY 宏观数据，`AUGUR_SKIP_MACRO_FETCH=1` 可关闭） |
| `runs.compare` | 与最近一次含大师分析的 RunBundle 比较 | — |
| `report.earnings_dossier` | dossier + 证据化分歧图 | — |
| `sec.financials.annual` | `edgar_fundamentals.fetch_annual_financials` | sec.gov |
| `filings.compare` | `FilingDeltaBuilder` | — |
| `covenant.review` | `CovenantReviewer` | — |
| `sec.form4.read` | SEC Form 4 交易 | sec.gov |
| `ownership.cluster_detect` | `InsiderAnalyzer.detect_clusters` | — |

### Citation 验证

`CitationValidator` 检查结论（claim）引用的证据是否都在证据清单中。当前 4 个内置 Skill 输出的是结构化报告而不是 claim 列表，因此该门槛在执行时不适用；Skill 若输出 claim，可按下面方式校验：

```python
from augur.skills.permissions import CitationValidator

cv = CitationValidator(skill_spec)
result = cv.validate_claims(claims, evidence_manifest)
print(result["coverage"], result["valid"], result["missing_evidence"])
```

## 自定义 Skill

可以编写并校验自己的清单，但**执行器只运行内置 Skill**——这是有意的安全边界（不自动执行第三方清单）。

```yaml
id: my-research-skill
version: 1.0.0
description: My custom research workflow
license: Apache-2.0
compatibility: ">=11,<12"
inputs_schema:
  required: [ticker]
required_capabilities:
  - sec.financials.annual
  - filings.compare
permissions:
  resources: [evidence.read]
  network_domains: [sec.gov]
evidence_policy:
  information_time_required: true
  missing: abstain
  min_claim_coverage: 0.90
workflow:
  - id: fetch
    uses: sec.financials.annual
  - id: compare
    uses: filings.compare
    needs: [fetch]
outputs_schema:
  required: [run_id, delta_report, evidence_manifest]
evals:
  fixtures: [my-skill-v1]
  gates: [citation_validity, no_lookahead]
```

```python
from pathlib import Path
from augur.skills.loader import load_skill

spec = load_skill(Path("path/to/my-skill.yaml"))
print(spec.id, spec.version)
```

## MCP

| 入口 | 用途 |
|---|---|
| 工具 `augur_run_skill(skill_id, ticker, inputs_json)` | 执行内置 Skill，返回 JSON 结果；RunBundle 可通过 `augur://runs/{run_id}` 读取 |
| Prompt `earnings_prep_prompt` | 财报前研究提示词 |
| Prompt `filing_delta_prompt` | Filing 变化对比提示词 |
| Prompt `thesis_review_prompt` | Thesis 审查 |
| Prompt `debt_covenant_review_prompt` | 债务约束审查 |
| Prompt `insider_cluster_review_prompt` | 内部人集群审查 |
| Prompt `capital_allocation_review_prompt` | 资本配置审查 |
| Prompt `accounting_quality_review_prompt` | 会计质量审查 |

## 参考

- [SkillSpec v1 Schema Reference](schema-reference.md)
- [Release Notes v11](RELEASE_NOTES_v11.md)
