# -*- coding: utf-8 -*-
"""Research report CLI — aggregated v11 research report."""
from __future__ import annotations

import click

from augur.research_report import ResearchReportBuilder


@click.command("research-report")
@click.argument("ticker")
@click.option("--format", "fmt", default="markdown", type=click.Choice(["markdown", "json"]))
def research_report_cmd(ticker, fmt):
    """Generate a comprehensive research report."""
    builder = ResearchReportBuilder()
    report = builder.build(ticker)
    if fmt == "json":
        click.echo(report.to_json())
    else:
        click.echo(report.to_markdown())
