# Schema Reference

五个核心 schema（`EvidenceItem` / `Claim` / `StepResult` / `RunBundle` / `SkillSpec`，均为冻结的 v1，位于 `src/augur/schemas/`）构成 Augur 的 evidence-first 数据合约。所有 schema 使用 Pydantic v2，支持 `model_validate()` / `model_dump()` round-trip。

## EvidenceItem

一个带三类时间语义的证据单元。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `evidence_id` | `str` | ✅ | `ev_{source}_{hash[:12]}`；正则 `^ev_[a-z0-9_.-]+_[a-f0-9]{12}$`（source 须小写） |
| `source` | `str` | ✅ | 数据源名称（`"sec_edgar"`, `"yfinance"` 等） |
| `source_locator` | `Optional[str]` | | URL 或 SEC accession number |
| `content_hash` | `str` | ✅ | 原始内容的 SHA-256 hex digest（至少 12 字符） |
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
| `coverage` | `Optional[float]` | | 0.0–1.0 覆盖率（`ge=0, le=1`） |
| `missing` | `bool` | | 预期的数据点是否缺失（默认 `False`） |
| `degraded` | `bool` | | 数据质量是否降级（默认 `False`） |
| `license` | `Optional[str]` | | SPDX license |
| `redistribution_allowed` | `bool` | | 是否允许再分发（默认 `True`） |
| `metadata` | `Dict[str, Any]` | | 额外键值对（默认 `{}`） |

`generate_evidence_id(source, content_hash)` 返回 `ev_{source}_{content_hash[:12]}`。

### 验证规则

- `available_at` 与 `retrieved_at` 都已设置且相等 → 拒绝（防止时间替代）
- `evidence_id` 必须以 `ev_{source}_` 开头（`source` 为本条证据的 `source` 字段）

---

## Claim

带分类证据引用的声明。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `claim_id` | `str` | ✅ | `cl_{hash[:12]}`（text 的 SHA-256 前 12 位）；正则 `^cl_[a-f0-9]{12}$` |
| `text` | `str` | ✅ | 声明文本（至少 1 字符） |
| `persona_id` | `str` | ✅ | 做出此声明的 persona |
| `supports` | `List[str]` | | 支持性 evidence IDs |
| `contradicts` | `List[str]` | | 矛盾性 evidence IDs |
| `insufficient` | `List[str]` | | 不足 evidence IDs |
| `classification` | `ClaimClassification` | ✅ | `fact` / `inference` / `scenario` |
| `confidence` | `Optional[float]` | | 0.0–1.0（`ge=0, le=1`） |
| `confidence_source` | `Optional[ConfidenceSource]` | | `explicit_rule` / `calibrated_model` |
| `status` | `ClaimStatus` | | `active` / `unknown` / `abstain`（默认 `active`） |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### 验证规则

- `confidence` 必须有 `confidence_source`
- `supports` 与 `contradicts` 均为空时 → `status` 必须为 `unknown` 或 `abstain`（`insufficient` 不计入）

`generate_claim_id(text)` 返回 `cl_{sha256(text)[:12]}`。

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
| `result` | `Any` | | typed 结果（dict/list/number/bool，**不能是纯字符串**；默认 `None`） |
| `diagnostics` | `Optional[str]` | | 错误/诊断信息 |
| `provenance` | `Optional[str]` | | 来源链 |
| `elapsed_ms` | `Optional[float]` | | 耗时（毫秒，`ge=0`） |
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
| `run_id` | `str` | ✅ | `run_{ticker}_{timestamp}_{hash[:8]}`；`timestamp` 格式 `%Y%m%dT%H%M%S`（如 `20260719T093000`）；正则 `^run_[A-Z0-9_.-]+_\d{8}T\d{6}_[a-f0-9]{8}$`（ticker 须大写） |
| `created_at` | `datetime` | ✅ | 创建时间 |
| `supersedes` | `Optional[str]` | | 被替代的 run_id |
| `manifest` | `RunManifest` | ✅ | 输入快照 + 版本信息 |
| `step_results` | `List[StepResult]` | ✅（实际） | 有序步骤结果；字段有默认值 `[]`，但验证器要求至少 1 项 |
| `coverage` | `CoverageStats` | | 覆盖/缺失/降级统计（默认全 0） |
| `metadata` | `Dict[str, Any]` | | 额外键值对 |

### Sub-model: `RunManifest`

| 字段 | 类型 | 说明 |
|---|---|---|
| `input_snapshot_hash` | `str`（必填） | 运行时全部输入数据的 hash |
| `config_version` | `str`（必填） | 配置版本 |
| `model_version` | `str`（必填） | 模型版本 |
| `code_version` | `str`（必填） | 代码版本 |

### Sub-model: `CoverageStats`

| 字段 | 类型 | 说明 |
|---|---|---|
| `total_evidence` | `int`（默认 0，`ge=0`） | 预期证据总数 |
| `covered_evidence` | `int`（默认 0，`ge=0`） | coverage ≥ 阈值的证据数 |
| `missing_evidence` | `int`（默认 0，`ge=0`） | 标记为 missing 的证据数 |
| `degraded_evidence` | `int`（默认 0，`ge=0`） | 标记为 degraded 的证据数 |
| `coverage_ratio` | `float`（默认 0.0，0.0–1.0） | covered / total |

### 验证规则

- `supersedes` 不能等于 `run_id`
- `step_results` 不能为空（至少 1 项）

`generate_run_id(ticker, timestamp, manifest_hash)` 返回 `run_{ticker}_{timestamp:%Y%m%dT%H%M%S}_{manifest_hash[:8]}`。`RunBundle` 创建后视为不可变；`supersedes` 只引用被替代的旧 run，不修改旧 bundle。

---

## SkillSpec v1

声明式 Skill 规范。**严格禁止可执行内容**。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | `str` | ✅ | 小写开头的标识，正则 `^[a-z][a-z0-9_-]{0,63}$`（`"earnings-prep"`） |
| `version` | `str` | | semver，默认 `"1.0.0"`，正则 `^\d+\.\d+\.\d+` |
| `description` | `str` | ✅ | 一句话描述（至少 1 字符） |
| `license` | `Optional[str]` | | SPDX |
| `compatibility` | `str` | | 版本约束字符串，默认 `""`（`">=11,<12"`） |
| `inputs_schema` | `Dict[str, Any]` | | JSON Schema |
| `required_capabilities` | `List[str]` | | 依赖的 Capability 名称 |
| `permissions` | `SkillPermissions` | | 资源/网络/文件权限 |
| `evidence_policy` | `EvidencePolicy` | | 证据策略 |
| `workflow` | `List[WorkflowStep]` | | 有序步骤 |
| `outputs_schema` | `Dict[str, Any]` | | JSON Schema |
| `evals` | `SkillEvals` | | fixtures + gates |

`SkillSpec` 没有 `metadata` 字段。

### 子模型

| 模型 | 字段 |
|---|---|
| `SkillPermissions` | `resources: List[str]`、`network_domains: List[str]`（仅主机名，无 scheme），默认均为空 |
| `EvidencePolicy` | `information_time_required: bool = True`、`missing_strategy: MissingStrategy = abstain`（`abstain` / `flag` / `estimate`）、`min_claim_coverage: float = 0.0`（0.0–1.0） |
| `WorkflowStep` | `id: str`（必填，workflow 内唯一）、`uses: str`（必填）、`needs: List[str] = []` |
| `SkillEvals` | `fixtures: List[Any]`、`gates: List[Any]`；字符串或结构化对象均可（结构化形式见 `EvalFixture{input, expected_output}` / `EvalGate{metric, threshold}`） |

### 验证规则

- workflow 步骤 `id` 必须唯一（Pydantic 验证器）

### 禁止内容（`validate_skill_spec(spec: dict) -> List[str]`，返回违规列表，空列表即合法）

- 缺少非空字符串 `id` / `description`
- 键名（不区分大小写）精确等于 `import`、`shell`、`exec`、`eval`、`compile`，或包含 `module_path`、`subprocess`、`os.system`、`__import__`
- 文件系统路径字符串（`/abs`、`./rel`、`../up`；`http(s)://` URL 除外）
- URL 的主机不在 `permissions.network_domains` 中（`"*"` 表示放行）

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
