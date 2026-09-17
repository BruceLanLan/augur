# -*- coding: utf-8 -*-
"""`augur skill` — list, inspect and run the built-in declarative skills."""
from __future__ import annotations

import click


@click.group("skill")
def skill_cmd():
    """Run built-in research skills (earnings-prep, filing-delta, …).

    Not to be confused with `augur skills`, which lists persona skill packs
    for Hermes / OpenClaw.
    """


@skill_cmd.command("list")
def skill_list_cmd():
    """List built-in skills."""
    from augur.skills.loader import load_builtin_skills

    for spec in load_builtin_skills():
        steps = " → ".join(s.id for s in spec.workflow)
        click.echo(f"{spec.id:<24} v{spec.version}  {spec.description}")
        click.echo(f"{'':<24} steps: {steps}")


@skill_cmd.command("show")
@click.argument("skill_id")
def skill_show_cmd(skill_id):
    """Show a skill's inputs, capabilities and permissions."""
    from augur.capability import get_capability_registry
    from augur.skills.runner import SkillNotRunnable, get_builtin_skill

    try:
        spec = get_builtin_skill(skill_id)
    except SkillNotRunnable as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    reg = get_capability_registry()
    click.echo(f"{spec.id} v{spec.version} — {spec.description}")
    click.echo(f"inputs: required {spec.inputs_schema.get('required', [])}, optional {spec.inputs_schema.get('optional', [])}")
    click.echo(f"permissions: resources {spec.permissions.resources}, network {spec.permissions.network_domains}")
    click.echo("workflow:")
    for step in spec.workflow:
        cap = reg.get(step.uses) if step.uses in reg.list_all() else None
        detail = f"{cap.description} [network: {', '.join(cap.network_domains) or 'none'}]" if cap else "NOT IMPLEMENTED"
        needs = f" (needs {', '.join(step.needs)})" if step.needs else ""
        click.echo(f"  {step.id}: {step.uses}{needs} — {detail}")
    click.echo(f"outputs: {spec.outputs_schema.get('required', [])}")


@skill_cmd.command("run")
@click.argument("skill_id")
@click.argument("ticker")
@click.option("--set", "extra", multiple=True, metavar="KEY=VALUE",
              help="Optional input, e.g. --set debt_ebitda_max=3.0 (repeatable).")
@click.option("--json", "as_json", is_flag=True, help="Print the full result as JSON.")
def skill_run_cmd(skill_id, ticker, extra, as_json):
    """Run a skill, e.g. `augur skill run filing-delta AAPL`."""
    import dataclasses
    import json

    from augur.skills.permissions import SkillPermissionError
    from augur.skills.runner import SkillNotRunnable, run_skill

    inputs = {"ticker": ticker}
    for item in extra:
        if "=" not in item:
            click.echo(f"Error: --set expects KEY=VALUE, got {item!r}", err=True)
            raise SystemExit(1)
        key, value = item.split("=", 1)
        inputs[key.strip()] = value.strip()
    try:
        result = run_skill(skill_id, inputs)
    except (SkillNotRunnable, SkillPermissionError) as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(dataclasses.asdict(result), ensure_ascii=False, indent=2, default=str))
    else:
        if result.outputs.get("summary_markdown"):
            click.echo(result.outputs["summary_markdown"])
            click.echo("")
        click.echo(f"Skill: {result.skill_id} · status: {result.status}")
        click.echo("Steps: " + ", ".join(f"{k}={v}" for k, v in result.step_status.items()))
        click.echo(f"Evidence items: {len(result.outputs.get('evidence_manifest', []))}")
        click.echo(f"Run ID: {result.run_id}  (augur export {ticker.upper()} --run-id {result.run_id})")
        if result.error:
            click.echo(f"Error: {result.error}", err=True)
    if result.status != "success":
        raise SystemExit(1)
