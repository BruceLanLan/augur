# -*- coding: utf-8 -*-
"""
Skill runner — execute a built-in SkillSpec's declarative workflow.

Scope, deliberately small:

* Only skills returned by :func:`augur.skills.loader.load_builtin_skills`
  run. Third-party manifests are not loaded or executed.
* Steps run sequentially in dependency order (``needs``); no retries, no
  parallelism.
* **Pre-flight before anything executes**: every step's capability must be
  declared in ``required_capabilities``, registered, and implemented, and
  every network domain / local resource the capability touches must be
  allowed by the skill's ``permissions``. Any violation raises before the
  first handler runs. Allowed and denied checks are both written to the
  audit trail stored in the RunBundle.
* Each step is wrapped in :class:`augur.run_tracker.RunTracker`; its
  evidence ids become ``output_refs`` and the RunBundle is persisted like a
  workflow run, so ``augur export`` / ``research-report`` work on it.
* Outputs are checked against ``outputs_schema.required``.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from augur.capability import CapabilityRegistry, get_capability_registry
from augur.schemas.skill_spec import SkillSpec
from augur.skills.permissions import SkillPermissionEnforcer, SkillPermissionError


class SkillNotRunnable(Exception):
    """The skill cannot run: unknown id, bad inputs, or an unimplemented step."""


@dataclass
class SkillRunResult:
    skill_id: str
    run_id: str
    status: str                      # "success" | "failed"
    outputs: Dict[str, Any] = field(default_factory=dict)
    step_status: Dict[str, str] = field(default_factory=dict)
    audit_log: List[str] = field(default_factory=list)
    error: str = ""


def get_builtin_skill(skill_id: str) -> SkillSpec:
    from augur.skills.loader import load_builtin_skills

    for spec in load_builtin_skills():
        if spec.id == skill_id:
            return spec
    known = ", ".join(sorted(s.id for s in load_builtin_skills()))
    raise SkillNotRunnable(f"unknown skill {skill_id!r} (built-in skills: {known})")


def _ordered_steps(spec: SkillSpec) -> list:
    ids = {step.id for step in spec.workflow}
    for step in spec.workflow:
        unknown = [n for n in step.needs if n not in ids]
        if unknown:
            raise SkillNotRunnable(f"step {step.id!r} needs unknown step(s): {', '.join(unknown)}")
    done: List[str] = []
    ordered = []
    pending = list(spec.workflow)
    while pending:
        ready = [s for s in pending if all(n in done for n in s.needs)]
        if not ready:
            raise SkillNotRunnable("workflow has a dependency cycle: " + ", ".join(s.id for s in pending))
        for step in ready:  # keep manifest order among ready steps
            ordered.append(step)
            done.append(step.id)
            pending.remove(step)
    return ordered


def _jsonable(value: Any) -> Any:
    """Drop in-memory ``_``-prefixed keys and make the rest JSON-safe."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return json.loads(json.dumps(value, default=str))


class SkillRunner:
    def __init__(self, spec: SkillSpec, registry: Optional[CapabilityRegistry] = None):
        self.spec = spec
        self.registry = registry or get_capability_registry()
        self.enforcer = SkillPermissionEnforcer(spec)
        self._allowed: List[str] = []

    # ------------------------------------------------------------------
    def preflight(self) -> list:
        """Validate every step before any executes; returns steps in run order."""
        steps = _ordered_steps(self.spec)
        for step in steps:
            self.enforcer.check_capability(step.uses)  # raises SkillPermissionError
            self._allowed.append(f"ALLOWED capability '{step.uses}' for step '{step.id}'")
            try:
                cap = self.registry.get(step.uses)
            except KeyError:
                raise SkillNotRunnable(f"capability {step.uses!r} (step {step.id!r}) is not implemented")
            for domain in cap.network_domains:
                self.enforcer.check_network(domain)
                self._allowed.append(f"ALLOWED network domain '{domain}' for '{step.uses}'")
            for resource in cap.resources:
                self.enforcer.check_resource(resource)
                self._allowed.append(f"ALLOWED resource '{resource}' for '{step.uses}'")
        return steps

    def _inputs(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        inputs = {k: v for k, v in raw.items() if v not in (None, "")}
        if "ticker" in inputs:
            inputs["ticker"] = str(inputs["ticker"]).upper()
        declared = set(self.spec.inputs_schema.get("optional", [])) | set(self.spec.inputs_schema.get("required", []))
        if "as_of" in declared:
            inputs.setdefault("as_of", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        if "event_id" in declared:
            inputs.setdefault("event_id", f"{inputs.get('ticker', '')}_next")
        missing = [k for k in self.spec.inputs_schema.get("required", []) if k not in inputs]
        if missing:
            raise SkillNotRunnable(f"missing required input(s): {', '.join(missing)}")
        unknown = sorted(set(inputs) - declared)
        if unknown:
            raise SkillNotRunnable(f"unknown input(s) for {self.spec.id}: {', '.join(unknown)}")
        return inputs

    # ------------------------------------------------------------------
    def run(self, raw_inputs: Dict[str, Any]) -> SkillRunResult:
        from augur.run_tracker import RunTracker
        from augur.schemas.step_result import StepStatus
        from augur.team_audit import record_action

        inputs = self._inputs(raw_inputs)
        try:
            steps = self.preflight()
        except SkillPermissionError:
            record_action("skill_denied", {"skill": self.spec.id, "audit": self.enforcer.audit_log})
            raise

        tracker = RunTracker(ticker=inputs.get("ticker", "SKILL"))
        tracker.start_run(input_snapshot_hash=hashlib.sha256(
            json.dumps({"skill": self.spec.id, "version": self.spec.version, "inputs": inputs},
                       sort_keys=True).encode()).hexdigest())

        outputs: Dict[str, Dict[str, Any]] = {}
        step_status: Dict[str, str] = {}
        evidence: Dict[str, Dict[str, Any]] = {}
        error = ""
        for step in steps:
            cap = self.registry.get(step.uses)
            errors = self.registry.validate_request(step.uses, inputs)
            sid = tracker.start_step(step.id)
            if errors:
                error = f"step {step.id!r}: invalid inputs for {step.uses}: {'; '.join(errors)}"
            else:
                upstream = {n: outputs[n] for n in step.needs}
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                future = pool.submit(cap.handler, inputs, upstream)
                try:
                    outputs[step.id] = future.result(timeout=cap.timeout_ms / 1000)
                except concurrent.futures.TimeoutError:
                    error = f"step {step.id!r} ({step.uses}) exceeded its {cap.timeout_ms} ms timeout"
                except Exception as exc:  # handler failure: record it, stop the run
                    error = f"step {step.id!r} ({step.uses}) failed: {exc}"
                finally:
                    pool.shutdown(wait=False)
            if error:
                tracker.finish_step(sid, StepStatus.FAILURE, diagnostics=error)
                step_status[step.id] = "failure"
                break
            items = [e for e in outputs[step.id].get("evidence_items", []) if isinstance(e, dict) and e.get("evidence_id")]
            for item in items:
                evidence[item["evidence_id"]] = item
            tracker.finish_step(sid, StepStatus.SUCCESS, result=_jsonable(outputs[step.id]),
                                output_refs=[e["evidence_id"] for e in items])
            step_status[step.id] = "success"

        merged: Dict[str, Any] = {}
        for step in steps:
            merged.update(_jsonable(outputs.get(step.id, {})))
        merged.pop("evidence_items", None)
        merged["run_id"] = tracker.run_id
        merged["evidence_manifest"] = sorted(evidence)
        missing_outputs = [k for k in self.spec.outputs_schema.get("required", []) if k not in merged]
        if not error and missing_outputs:
            error = f"outputs missing required key(s): {', '.join(missing_outputs)}"

        audit = self._allowed + self.enforcer.audit_log
        if evidence:
            tracker.record_evidence_coverage(list(evidence.values()))
        tracker.set_run_metadata("skill", {
            "id": self.spec.id, "version": self.spec.version, "inputs": inputs,
            "status": "failed" if error else "success", "error": error,
            "audit_log": audit, "evidence_policy": self.spec.evidence_policy.model_dump(mode="json"),
        })
        tracker.finish_run()
        record_action("skill_run", {"skill": self.spec.id, "run_id": tracker.run_id,
                                    "status": "failed" if error else "success"})
        return SkillRunResult(
            skill_id=self.spec.id, run_id=tracker.run_id, status="failed" if error else "success",
            outputs=merged, step_status=step_status, audit_log=audit, error=error,
        )


def run_skill(skill_id: str, inputs: Dict[str, Any]) -> SkillRunResult:
    """Run a built-in skill by id."""
    return SkillRunner(get_builtin_skill(skill_id)).run(inputs)
