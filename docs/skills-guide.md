# Augur Skill 使用指南 (v11)

Skill 是声明式的研究 SOP（标准操作流程）。Skill 本身不包含可执行代码——它声明了需要哪些 Capability、允许访问哪些资源、以及工作流步骤。实际执行由 Augur 的 Capability Registry 和 Skill Runner 负责。

## 内置 Skills

v11 RC 包含两个内置 Skill：

### `earnings-prep` — 财报前研究包

为即将到来的财报事件生成 point-in-time 研究 dossier。

**触发条件**：watchlist 中有 ticker 的财报事件临近（默认 30 天内）

**做什么**：
1. 收集上次财报以来的 guidance、KPI 变化
2. 检查近期 filing、内部人交易、机构持仓变化
3. 运行 18 位 persona 分析，生成分歧图
4. 列出待验证问题和 bull/base/bear scenario 变量
5. 生成带 evidence manifest 的 RunBundle

**使用方式**：

```bash
# CLI
augur skill run earnings-prep --ticker AAPL --event-id Q4_2025

# MCP (via external agent)
mcp_augur_execute_skill(skill="earnings-prep", params={"ticker": "AAPL", "event_id": "Q4_2025"})
```

**权限**：只读 `evidence.read`、`runs.read`；网络仅 `sec.gov`

**证据策略**：`information_time_required: true`，缺失时 abstain，最低 claim 覆盖 95%

---

### `filing-delta` — Filing 变化对比

比较新 filing 与上一份之间的实质性变化，不生成无变化的噪声。

**做什么**：
1. 拉取新旧两份 SEC filing
2. 比较数字变化（revenue、EPS、guidance range 等）
3. 比较章节变化（risk factors、MD&A、legal proceedings）
4. 生成结构化 delta report，每项 change 链接到原文位置

**使用方式**：

```bash
augur skill run filing-delta --ticker AAPL \
  --new-accession 0000320193-25-000123 \
  --previous-accession 0000320193-24-000089
```

**权限**：只读 `evidence.read`、`runs.read`；网络仅 `sec.gov`

**证据策略**：`information_time_required: true`，缺失时 abstain，最低 claim 覆盖 90%

---

## Skill 安全模型

### v1 声明式合约

所有 Skill 必须通过 `validate_skill_spec()` 验证，v1 **严格禁止**：

- `module_path`、`import`、`shell`、`exec`、`eval`
- 任意文件路径
- 未注册的网络访问
- Python 表达式求值

### 运行时权限执行

```python
from augur.skills.permissions import SkillPermissionEnforcer

enf = SkillPermissionEnforcer(skill_spec)

enf.check_capability("sec.filings.read")    # ✅ 已声明 → 通过
enf.check_network("sec.gov")                # ✅ 已声明 → 通过
enf.check_network("evil.com")               # ❌ 未声明 → SkillPermissionError
enf.check_file_path("/etc/passwd")          # ❌ v1 默认禁止文件访问
```

所有拒绝记录写入 audit log。

### Citation 验证

```python
from augur.skills.permissions import CitationValidator

cv = CitationValidator(skill_spec)
result = cv.validate_claims(claims, evidence_manifest)

print(result["coverage"])          # 0.0-1.0
print(result["valid"])             # coverage ≥ min_claim_coverage
print(result["missing_evidence"])  # 缺失的证据 ID 列表
```

---

## 自定义 Skill

### SkillSpec YAML 格式

```yaml
id: my-research-skill
version: 1.0.0
description: My custom research workflow
license: Apache-2.0
compatibility: ">=11,<12"

inputs_schema:
  required: [ticker]

required_capabilities:
  - fundamentals.snapshot
  - runs.compare

permissions:
  resources: [evidence.read, runs.read]
  network_domains: [sec.gov]

evidence_policy:
  information_time_required: true
  missing: abstain
  min_claim_coverage: 0.90

workflow:
  - id: snapshot
    uses: fundamentals.snapshot
  - id: compare
    uses: runs.compare
    needs: [snapshot]

outputs_schema:
  required: [run_id, report, evidence_manifest]

evals:
  fixtures: [my-skill-v1]
  gates: [citation_validity, no_lookahead]
```

### 加载和验证

```python
from augur.skills.loader import load_skill
from pathlib import Path

spec = load_skill(Path("path/to/my-skill.yaml"))
print(spec.id, spec.version)
```

---

## 参考

- [SkillSpec v1 Schema Reference](schema-reference.md)
- [Capability Registry API](#) (待完善)
- [Release Notes v11](RELEASE_NOTES_v11.md)
