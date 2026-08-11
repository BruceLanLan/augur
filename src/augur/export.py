# -*- coding: utf-8 -*-
"""
augur.export — Markdown / JSON / PDF / Evidence Pack export for RunBundle.

Provides ``ReportExporter`` with four export formats:

* ``to_markdown`` — structured Markdown report with claims, evidence, provenance.
* ``to_json`` — full RunBundle JSON with schema version and export timestamp.
* ``to_pdf`` — PDF via markdown → HTML → weasyprint/pdfkit (optional deps).
* ``export_evidence_pack`` — distributable .zip with manifest, run bundle, and
  all referenced EvidenceItem JSON files.

CLI integration::

    augur export AAPL --run-id run_AAPL_xxx --format md
    augur export AAPL --run-id run_AAPL_xxx --format pdf
    augur export AAPL --run-id run_AAPL_xxx --format evidence-pack
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, BaseLoader, TemplateNotFound

from augur.data_dir import get_data_dir
from augur.schemas.run_bundle import RunBundle
from augur.schemas.step_result import StepResult, StepStatus
from augur.schemas.claim import Claim
from augur.schemas.evidence import EvidenceItem


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPORT_SCHEMA_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Default Jinja2 template for Markdown export
# ---------------------------------------------------------------------------

DEFAULT_MD_TEMPLATE = """\
# Augur Analysis Report: {{ bundle.metadata.get('ticker', bundle.run_id) }}

**Run ID**: `{{ bundle.run_id }}`
**Created**: {{ bundle.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if bundle.created_at else 'N/A' }}
{% if bundle.supersedes %}
**Supersedes**: `{{ bundle.supersedes }}`
{% endif %}

---

## Summary

- **Steps executed**: {{ bundle.step_results|length }}
- **Successful**: {{ steps_success }}
- **Failed**: {{ steps_failed }}
- **Degraded**: {{ steps_degraded }}
- **Coverage ratio**: {{ "%.1f"|format(bundle.coverage.coverage_ratio * 100) }}%

{% if claims %}
- **Claims**: {{ claims|length }}
{% for claim in claims %}
  - `{{ claim.claim_id }}` [{{ claim.classification.value }}] {{ claim.text[:80] }}{% if claim.text|length > 80 %}...{% endif %}
{% endfor %}
{% endif %}

---

## Step Results

{% for step in bundle.step_results %}
### Step {{ loop.index }}: {{ step.step_name }}

| Field | Value |
|-------|-------|
| Step ID | `{{ step.step_id }}` |
| Status | **{{ step.status.value }}** |
| Started | {{ step.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if step.started_at else 'N/A' }} |
| Finished | {{ step.finished_at.strftime('%Y-%m-%d %H:%M:%S UTC') if step.finished_at else 'N/A' }} |
{% if step.elapsed_ms %}
| Elapsed | {{ "%.1f"|format(step.elapsed_ms) }} ms |
{% endif %}
{% if step.content_hash %}
| Content Hash | `{{ step.content_hash[:16] }}...` |
{% endif %}

{% if step.input_refs %}
**Input References**: {{ step.input_refs|join(', ') }}
{% endif %}

{% if step.output_refs %}
**Output References**: {{ step.output_refs|join(', ') }}
{% endif %}

{% if step.diagnostics %}
**Diagnostics**:
```
{{ step.diagnostics }}
```
{% endif %}

{% if step.result is not none %}
**Result**:
```json
{{ step.result | tojson(indent=2) }}
```
{% endif %}

{% endfor %}

---

{% if claims %}
## Claims

{% for claim in claims %}
### Claim `{{ claim.claim_id }}`

- **Text**: {{ claim.text }}
- **Persona**: `{{ claim.persona_id }}`
- **Classification**: {{ claim.classification.value }}
- **Status**: {{ claim.status.value }}
{% if claim.confidence is not none %}
- **Confidence**: {{ "%.0f"|format(claim.confidence * 100) }}% (source: {{ claim.confidence_source.value if claim.confidence_source else 'N/A' }})
{% endif %}
{% if claim.supports %}
- **Supporting Evidence**: {{ claim.supports|join(', ') }}
{% endif %}
{% if claim.contradicts %}
- **Contradicting Evidence**: {{ claim.contradicts|join(', ') }}
{% endif %}
{% if claim.insufficient %}
- **Insufficient Evidence**: {{ claim.insufficient|join(', ') }}
{% endif %}

{% endfor %}
{% endif %}

---

{% if evidence_items %}
## Evidence

{% for ev in evidence_items %}
### Evidence `{{ ev.evidence_id }}`

| Field | Value |
|-------|-------|
| Source | {{ ev.source }} |
| Instrument | {{ ev.instrument or 'N/A' }} |
| Metric | {{ ev.metric or 'N/A' }} |
{% if ev.value is not none %}
| Value | {{ ev.value }}{% if ev.unit %} {{ ev.unit }}{% endif %} |
{% endif %}
{% if ev.effective_at %}
| Effective | {{ ev.effective_at.strftime('%Y-%m-%d') }} |
{% endif %}
{% if ev.available_at %}
| Available | {{ ev.available_at.strftime('%Y-%m-%d') }} |
{% endif %}
| Schema Version | {{ ev.schema_version }} |
{% if ev.coverage is not none %}
| Coverage | {{ "%.0f"|format(ev.coverage * 100) }}% |
{% endif %}
{% if ev.missing %}
| ⚠️  Missing | Yes |
{% endif %}
{% if ev.degraded %}
| ⚠️  Degraded | Yes |
{% endif %}

{% endfor %}
{% endif %}

---

## Provenance

| Field | Value |
|-------|-------|
| Schema Version | {{ bundle.manifest.schema_version if bundle.manifest else 'N/A' }} |
| Config Version | {{ bundle.manifest.config_version if bundle.manifest else 'N/A' }} |
| Model Version | {{ bundle.manifest.model_version if bundle.manifest else 'N/A' }} |
| Code Version | {{ bundle.manifest.code_version if bundle.manifest else 'N/A' }} |
| Input Snapshot Hash | `{{ bundle.manifest.input_snapshot_hash[:16] if bundle.manifest else 'N/A' }}...` |
| Export Timestamp | {{ export_timestamp }} |

---

*Report generated by Augur Agents — schema v{{ export_schema_version }}*
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_claims_from_bundle(bundle: RunBundle) -> List[Claim]:
    """Extract Claim objects from RunBundle step results.

    Walks through step_results looking for claims in the result field
    or in output_refs that reference claim patterns.
    """
    claims: List[Claim] = []
    seen_ids: set = set()

    for step in bundle.step_results:
        result = step.result
        if not isinstance(result, dict):
            continue

        # Look for a "claims" key in step results
        for key in ("claims", "all_claims"):
            claim_list = result.get(key, [])
            if isinstance(claim_list, list):
                for cdata in claim_list:
                    if isinstance(cdata, dict) and "claim_id" in cdata:
                        try:
                            claim = Claim.model_validate(cdata)
                            if claim.claim_id not in seen_ids:
                                claims.append(claim)
                                seen_ids.add(claim.claim_id)
                        except Exception:
                            pass

    return claims


def _extract_evidence_from_bundle(bundle: RunBundle) -> List[EvidenceItem]:
    """Extract EvidenceItem objects from RunBundle step results.

    Walks through step_results looking for evidence in the result field.
    """
    evidence: List[EvidenceItem] = []
    seen_ids: set = set()

    for step in bundle.step_results:
        result = step.result
        if not isinstance(result, dict):
            continue

        # Look for evidence lists in step results
        for key in ("evidence", "all_evidence", "evidence_items"):
            ev_list = result.get(key, [])
            if isinstance(ev_list, list):
                for edata in ev_list:
                    if isinstance(edata, dict) and "evidence_id" in edata:
                        try:
                            ev = EvidenceItem.model_validate(edata)
                            if ev.evidence_id not in seen_ids:
                                evidence.append(ev)
                                seen_ids.add(ev.evidence_id)
                        except Exception:
                            pass

    return evidence


def _collect_evidence_ids_from_claims(claims: List[Claim]) -> set:
    """Collect all evidence IDs referenced by claims."""
    ids: set = set()
    for claim in claims:
        ids.update(claim.supports)
        ids.update(claim.contradicts)
        ids.update(claim.insufficient)
    return ids


def _load_run_bundle(run_id: str, data_dir: Optional[Path] = None) -> RunBundle:
    """Load a RunBundle from disk by run_id.

    Args:
        run_id: The run identifier (e.g. ``run_AAPL_20250101T120000_abc12345``).
        data_dir: Optional custom data directory. Defaults to ``get_data_dir()``.

    Returns:
        The loaded RunBundle.

    Raises:
        FileNotFoundError: If the run bundle file does not exist.
        ValueError: If the file cannot be parsed as a RunBundle.
    """
    if data_dir is None:
        data_dir = get_data_dir()

    run_path = data_dir / "runs" / f"{run_id}.json"
    if not run_path.exists():
        raise FileNotFoundError(
            f"RunBundle not found: {run_path}\n"
            f"  Run ID: {run_id}\n"
            f"  Check available runs with: augur history"
        )

    raw = json.loads(run_path.read_text(encoding="utf-8"))
    try:
        return RunBundle.model_validate(raw)
    except Exception as e:
        raise ValueError(
            f"Failed to parse RunBundle from {run_path}: {e}"
        ) from e


# ---------------------------------------------------------------------------
# ReportExporter
# ---------------------------------------------------------------------------

class ReportExporter:
    """Export RunBundle analysis results in multiple formats.

    Parameters:
        data_dir: Optional override for the augur data directory.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self._data_dir = data_dir

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    def to_markdown(
        self,
        run_bundle: RunBundle,
        template: str = "default",
    ) -> str:
        """Generate a structured Markdown report from a RunBundle.

        Args:
            run_bundle: The analysis run to export.
            template: Template name. ``"default"`` uses the built-in
                template. Supply a custom Jinja2 template string for
                custom layouts.

        Returns:
            Rendered Markdown string.
        """
        claims = _extract_claims_from_bundle(run_bundle)
        evidence_items = _extract_evidence_from_bundle(run_bundle)

        # Template context
        ctx: Dict[str, Any] = {
            "bundle": run_bundle,
            "claims": claims,
            "evidence_items": evidence_items,
            "steps_success": sum(
                1 for sr in run_bundle.step_results
                if sr.status == StepStatus.SUCCESS
            ),
            "steps_failed": sum(
                1 for sr in run_bundle.step_results
                if sr.status == StepStatus.FAILURE
            ),
            "steps_degraded": sum(
                1 for sr in run_bundle.step_results
                if sr.status == StepStatus.DEGRADED
            ),
            "export_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "export_schema_version": EXPORT_SCHEMA_VERSION,
        }

        if template == "default":
            tmpl_str = DEFAULT_MD_TEMPLATE
        else:
            tmpl_str = template

        env = Environment(loader=BaseLoader())
        try:
            tpl = env.from_string(tmpl_str)
            return tpl.render(**ctx)
        except Exception as e:
            raise ValueError(f"Template rendering failed: {e}") from e

    # ------------------------------------------------------------------
    # JSON
    # ------------------------------------------------------------------

    def to_json(self, run_bundle: RunBundle) -> str:
        """Export the full RunBundle as a formatted JSON string.

        Includes:

        * ``export_schema_version``
        * ``export_timestamp``
        * Full ``run_bundle`` with inline EvidenceItem details from step results.

        Args:
            run_bundle: The analysis run to export.

        Returns:
            Indented JSON string.
        """
        claims = _extract_claims_from_bundle(run_bundle)
        evidence_items = _extract_evidence_from_bundle(run_bundle)

        payload: Dict[str, Any] = {
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "export_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "run_bundle": json.loads(
                run_bundle.model_dump_json()
            ),
            "claims": [json.loads(c.model_dump_json()) for c in claims],
            "evidence_items": [
                json.loads(e.model_dump_json()) for e in evidence_items
            ],
        }

        return json.dumps(payload, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------

    def to_pdf(
        self,
        run_bundle: RunBundle,
        output_path: Path,
    ) -> Path:
        """Export the RunBundle as a PDF file.

        Uses ``markdown`` → HTML → ``weasyprint`` for conversion.
        Falls back to writing a ``.md`` file if PDF dependencies are
        not installed.

        Args:
            run_bundle: The analysis run to export.
            output_path: Destination file path (should end with ``.pdf``).

        Returns:
            Path to the written PDF file (or ``.md`` fallback).

        Raises:
            ImportError: If no PDF backend is available (with install hint).
        """
        md_content = self.to_markdown(run_bundle)

        # Try weasyprint first
        try:
            import markdown as md_lib
            html = md_lib.markdown(md_content, extensions=["tables", "fenced_code", "codehilite"])

            # Wrap in minimal HTML document
            html_doc = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Augur Report: {run_bundle.run_id}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 960px; margin: 40px auto; padding: 0 20px; line-height: 1.6; }}
h1, h2, h3 {{ color: #1a1a2e; }}
table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background-color: #f4f4f8; }}
code {{ background: #f0f0f5; padding: 2px 6px; border-radius: 3px; }}
pre {{ background: #f4f4f8; padding: 16px; border-radius: 6px; overflow-x: auto; }}
</style>
</head>
<body>
{html}
</body>
</html>"""

            output_path = output_path.with_suffix(".pdf")
            weasyprint_available = False
            try:
                from weasyprint import HTML
                weasyprint_available = True
            except ImportError:
                pass

            if weasyprint_available:
                from weasyprint import HTML
                HTML(string=html_doc).write_pdf(str(output_path))
                return output_path

            # Try pdfkit fallback
            try:
                import pdfkit
                pdfkit.from_string(html_doc, str(output_path))
                return output_path
            except ImportError:
                pass

        except ImportError:
            pass

        # Fallback: write .md and provide install hint
        fallback_path = output_path.with_suffix(".md")
        fallback_path.write_text(md_content, encoding="utf-8")

        hint = (
            f"PDF dependencies not available. Markdown written to {fallback_path}.\n"
            f"  Install PDF support: pip install 'augur-agents[export]'\n"
            f"  Or install manually: pip install markdown weasyprint"
        )
        raise ImportError(hint)

    # ------------------------------------------------------------------
    # Evidence Pack
    # ------------------------------------------------------------------

    def export_evidence_pack(
        self,
        run_bundle: RunBundle,
        output_dir: Path,
    ) -> Path:
        """Create a distributable evidence pack as a ``.zip`` archive.

        Contents:

        * ``manifest.json`` — metadata (run_id, export timestamp, schema version).
        * ``run_bundle.json`` — the full RunBundle.
        * ``evidence/`` — directory with one JSON file per referenced
          :class:`EvidenceItem`, named ``{evidence_id}.json``.

        The archive is validated before returning: every evidence ID
        referenced in claims must be resolvable to a file inside the pack.

        Args:
            run_bundle: The analysis run to export.
            output_dir: Directory where the ``.zip`` will be written.

        Returns:
            Path to the created ``.zip`` file.

        Raises:
            ValueError: If validation fails (unresolvable evidence IDs).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        claims = _extract_claims_from_bundle(run_bundle)
        evidence_items = _extract_evidence_from_bundle(run_bundle)

        # Build evidence index
        evidence_by_id: Dict[str, EvidenceItem] = {
            ev.evidence_id: ev for ev in evidence_items
        }

        # Collect all referenced evidence IDs from claims
        referenced_ids = _collect_evidence_ids_from_claims(claims)
        for ev_id in referenced_ids:
            if ev_id not in evidence_by_id:
                # Create a placeholder for referenced but not inlined evidence
                evidence_by_id[ev_id] = EvidenceItem(
                    evidence_id=ev_id,
                    source="unknown",
                    content_hash=hashlib.sha256(b"placeholder").hexdigest(),
                    missing=True,
                )

        # Build manifest
        manifest: Dict[str, Any] = {
            "run_id": run_bundle.run_id,
            "export_schema_version": EXPORT_SCHEMA_VERSION,
            "export_timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "num_claims": len(claims),
            "num_evidence_items": len(evidence_by_id),
            "evidence_ids": sorted(evidence_by_id.keys()),
        }

        zip_name = f"evidence_pack_{run_bundle.run_id}"
        zip_path = output_dir / f"{zip_name}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # manifest.json
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2, ensure_ascii=False),
            )

            # run_bundle.json
            zf.writestr(
                "run_bundle.json",
                run_bundle.model_dump_json(indent=2),
            )

            # evidence/
            for ev_id, ev in sorted(evidence_by_id.items()):
                safe_name = ev_id.replace("/", "_").replace("\\", "_")
                zf.writestr(
                    f"evidence/{safe_name}.json",
                    ev.model_dump_json(indent=2),
                )

        # Validate: every evidence_id referenced by claims must be in the archive
        self._validate_evidence_pack(zip_path, referenced_ids)

        return zip_path

    def _validate_evidence_pack(
        self,
        zip_path: Path,
        referenced_ids: set,
    ) -> None:
        """Validate that all referenced evidence IDs are resolvable in the zip."""
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())

        unresolved: List[str] = []
        for ev_id in sorted(referenced_ids):
            safe_name = f"evidence/{ev_id.replace('/', '_').replace('\\\\', '_')}.json"
            if safe_name not in names:
                unresolved.append(ev_id)

        if unresolved:
            raise ValueError(
                f"Evidence pack validation failed: {len(unresolved)} evidence ID(s) "
                f"not found in archive:\n  "
                + "\n  ".join(unresolved)
            )

    # ------------------------------------------------------------------
    # Convenience: load + export
    # ------------------------------------------------------------------

    def export_from_run_id(
        self,
        run_id: str,
        output_path: Path,
        fmt: str = "md",
        template: str = "default",
    ) -> Path:
        """Load a RunBundle by ID and export it in one call.

        Args:
            run_id: Run identifier (e.g. ``run_AAPL_xxx``).
            output_path: Destination file path.
            fmt: ``"md"``, ``"json"``, ``"pdf"``, or ``"evidence-pack"``.
            template: Template name/string for markdown export.

        Returns:
            Path to the written output file.

        Raises:
            FileNotFoundError: If the run bundle is not found.
            ValueError: If the format is unknown.
        """
        bundle = _load_run_bundle(run_id, self._data_dir)

        fmt_lower = fmt.lower()
        if fmt_lower in ("md", "markdown"):
            md_content = self.to_markdown(bundle, template=template)
            out = output_path.with_suffix(".md")
            out.write_text(md_content, encoding="utf-8")
            return out
        elif fmt_lower == "json":
            json_content = self.to_json(bundle)
            out = output_path.with_suffix(".json")
            out.write_text(json_content, encoding="utf-8")
            return out
        elif fmt_lower == "pdf":
            return self.to_pdf(bundle, output_path)
        elif fmt_lower in ("evidence-pack", "evidence_pack", "evidencepack"):
            return self.export_evidence_pack(bundle, output_path.parent)
        else:
            raise ValueError(
                f"Unknown export format: {fmt!r}. "
                f"Valid: md, json, pdf, evidence-pack"
            )
