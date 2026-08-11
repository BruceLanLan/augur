# Schema Reference (v11)

四个核心 schema 构成 Augur 的 evidence-first 数据合约。所有 schema 使用 Pydantic v2，支持 `model_validate()` / `model_dump()` round-trip。

## EvidenceItem

一个带三类时间语义的证据单元。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `evidence_id` | `str` | ✅ | `ev_{source}_{hash[:12]}` |
| `source` | `str` | ✅ | 数据源名称（`"sec_edgar"`, `"yfinance"` 等） |
| `source_locator` | `Optional[str]` | | URL 或 SEC accession number |
| `content_hash` | `str` | ✅ | SHA-256 of raw content |
| `instrument` | `Optional[str]` | | Ticker |
| `metric` | `Optional[str]` | | 指标名（`"revenue"`, `"insider_ownership"`） |
| `value` | `Optional[float]` | | 数值 |
| `unit` | `Optional[str]` | | 单位（`"USD"`, `"shares"`, `"ratio"`） |
| `currency` | `Optional[str]` | | ISO 4217 |
| `effective_at` | `Optional[datetime]` | | 业务时点（e.g. fiscal period end） |
| `available_at` | `Optional[datetime]` | | 市场最早可获得时间（**不能用 retrieved_at 替代**） |
| `retrieved_at` | `Optional[datetime]` | | 系统获取时间 |
| `transform_version` | `Optional[str]` | | 转换 pipeline 版本 |
| `schema_version` | `str` | | `"1.0"` |
| `code_version` | `Optional[str]` | | 代码版本 |
| `coverage` | `Optional[float]` | | 0.0–1.0 覆盖率 |
| `missing` | `bool` | | 预期的数据点是否缺失 |
| `degraded` | `bool` | | 数据质量是否降级 |
| `license` | `Optional[str]` | | SPDX license |
| `redistribution_allowed` | `bool` | | 是否允许再分发 |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### 验证规则

- `available_at == retrieved_at` → 拒绝（防止时间替代）
- `evidence_id` 必须以 `ev_{source}_` 开头

---

## Claim

带分类证据引用的声明。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `claim_id` | `str` | ✅ | `cl_{hash[:12]}` |
| `text` | `str` | ✅ | 声明文本 |
| `persona_id` | `str` | ✅ | 做出此声明的 persona |
| `supports` | `List[str]` | | 支持性 evidence IDs |
| `contradicts` | `List[str]` | | 矛盾性 evidence IDs |
| `insufficient` | `List[str]` | | 不足 evidence IDs |
| `classification` | `ClaimClassification` | ✅ | `fact` / `inference` / `scenario` |
| `confidence` | `Optional[float]` | | 0.0–1.0 |
| `confidence_source` | `Optional[ConfidenceSource]` | | `explicit_rule` / `calibrated_model` |
| `status` | `ClaimStatus` | | `active` / `unknown` / `abstain` |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### 验证规则

- `confidence` 必须有 `confidence_source`
- 无 `supports` 且无 `contradicts` 时 → `status` 必须为 `unknown` 或 `abstain`

---

## StepResult

工作流单步的 typed 输出。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `step_id` | `str` | ✅ | 唯一步骤 ID |
| `step_name` | `str` | ✅ | 步骤名（`"fetch"`, `"analyze"`） |
| `status` | `StepStatus` | ✅ | `success` / `failure` / `degraded` |
| `input_refs` | `List[str]` | | 输入 artifact 引用 |
| `output_refs` | `List[str]` | | 输出 artifact 引用 |
| `result` | `Any` | | typed 结果（dict/list/number/bool，**不能是纯字符串**） |
| `diagnostics` | `Optional[str]` | | 错误/诊断信息 |
| `provenance` | `Optional[str]` | | 来源链 |
| `elapsed_ms` | `Optional[float]` | | 耗时（毫秒） |
| `content_hash` | `Optional[str]` | | 输出完整性 hash |
| `started_at` | `Optional[datetime]` | | 开始时间 |
| `finished_at` | `Optional[datetime]` | | 结束时间 |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### 验证规则

- `result` 不能是 `str`（必须是 typed 值）

---

## RunBundle

完整一次运行的不可变记录。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `run_id` | `str` | ✅ | `run_{ticker}_{timestamp}_{hash[:8]}` |
| `created_at` | `datetime` | ✅ | 创建时间 |
| `supersedes` | `Optional[str]` | | 被替代的 run_id |
| `manifest` | `RunManifest` | ✅ | 输入快照 + 版本信息 |
| `step_results` | `List[StepResult]` | | 有序步骤结果 |
| `coverage` | `CoverageStats` | | 覆盖/缺失/降级统计 |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### Sub-model: `RunManifest`

| 字段 | 类型 | 说明 |
|---|---|---|
| `input_snapshot_hash` | `str` | 运行时全部输入数据的 hash |
| `config_version` | `str` | 配置版本 |
| `model_version` | `str` | 模型版本 |
| `code_version` | `str` | 代码版本 |

### Sub-model: `CoverageStats`

| 字段 | 类型 | 说明 |
|---|---|---|
| `total_evidence` | `int` | 预期证据总数 |
| `covered_evidence` | `int` | coverage ≥ 阈值的证据数 |
| `missing_evidence` | `int` | 标记为 missing 的证据数 |
| `degraded_evidence` | `int` | 标记为 degraded 的证据数 |
| `coverage_ratio` | `float` | covered / total |

### 验证规则

- `supersedes` 不能等于 `run_id`
- `step_results` 不能为空

---

## SkillSpec v1

声明式 Skill 规范。**严格禁止可执行内容**。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `str` | ✅ | kebab-case 标识（`"earnings-prep"`） |
| `version` | `str` | | semver（`"1.0.0"`） |
| `description` | `str` | ✅ | 一句话描述 |
| `license` | `Optional[str]` | | SPDX |
| `compatibility` | `str` | | Augur 版本约束（`">=11,<12"`） |
| `inputs_schema` | `Dict[str, Any]` | | JSON Schema |
| `required_capabilities` | `List[str]` | | 依赖的 Capability 名称 |
| `permissions` | `SkillPermissions` | | 资源/网络/文件权限 |
| `evidence_policy` | `EvidencePolicy` | | 证据策略 |
| `workflow` | `List[WorkflowStep]` | | 有序步骤 |
| `outputs_schema` | `Dict[str, Any]` | | JSON Schema |
| `evals` | `SkillEvals` | | fixtures + gates |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### 禁止的键（`validate_skill_spec` 拒绝）

`module_path`, `module`, `import`, `shell`, `command`, `script`, `exec`, `eval`, `file_path`, `python_path`

---

## 使用

```python
from augur.schemas import EvidenceItem, Claim, RunBundle, SkillSpec

# Round-trip
d = my_evidence.model_dump()
rehydrated = EvidenceItem.model_validate(d)

# ID generation
from augur.schemas import generate_evidence_id, generate_claim_id, generate_run_id
```
