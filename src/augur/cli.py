# -*- coding: utf-8 -*-
"""
augur.cli - Click-based command line interface

Commands:
  augur analyze TICKER [--persona ID] [--pe X] [--roe X] ...
  augur consensus TICKER [--pe X] [--roe X] ...
  augur list-personas
  augur mcp-server
  augur api [--port 8900]
  augur inject-soul
  augur telegram          - Start Telegram bot
  augur slack             - Start Slack bot
  augur wechat            - Start WeChat/WeCom bot
  augur lark              - Start Lark/Feishu bot
  augur cron-run          - Run watchlist analysis once
  augur cron-start        - Start scheduler daemon
  augur watchlist-add     - Add ticker to watchlist
  augur watchlist-show    - Show current watchlist
  augur workflow TICKER     - Multi-step agentic pipeline
  augur doctor [--offline]  - Diagnose local environment (SSL/TLS, API keys, data sources)

This file only defines the ``main`` group and wires up every command from
``augur.cli_commands`` (R7 -- was previously a single 1476-line file;
mirrors how ``dashboard/routes/*.py`` each define their own ``APIRouter``
and ``dashboard/app.py`` includes them all). Shared helpers used by more
than one command module live in ``augur.cli_helpers``.
"""

import click

from augur import __version__


@click.group()
@click.version_option(version=__version__, prog_name="augur")
@click.option("--no-color", is_flag=True, default=False, help="Disable color output and emojis")
@click.pass_context
def main(ctx, no_color):
    """Augur - Multi-agent investment analysis system.

    \b
    18 virtual investor personas analyze stocks from different perspectives
    and form consensus recommendations with Kelly position sizing.

    \b
    Quick start:
      augur analyze AAPL          # Full analysis with all 18 agents
      augur consensus NVDA        # Consensus recommendation
      augur list-personas         # Show all personas
      augur fetch TSLA            # Fetch real-time data
      augur workflow AAPL --steps fetch,analyze,consensus,committee
    """
    import os
    ctx.ensure_object(dict)
    # Respect --no-color flag or NO_COLOR env variable
    if no_color or os.environ.get("NO_COLOR", "") != "":
        _prev_no_color = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        ctx.obj["no_color"] = True

        # Restore original env state when CLI context closes
        def _restore_env():
            if _prev_no_color is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = _prev_no_color

        ctx.call_on_close(_restore_env)
    else:
        ctx.obj["no_color"] = False


from augur.cli_commands.analysis import analyze_cmd, consensus_cmd, report_cmd, list_personas_cmd
from augur.cli_commands.data import fetch_cmd, sentiment_cmd, guidance_cmd
from augur.cli_commands.workflow import workflow_cmd, chat_cmd, committee_cmd
from augur.cli_commands.backtest import backtest_cmd, ic_report_cmd
from augur.cli_commands.watchlist import (
    watchlist_add_cmd, watchlist_show_cmd, cron_run_cmd, cron_start_cmd,
)
from augur.cli_commands.integrations import (
    inject_soul_cmd, telegram_cmd, slack_cmd, wechat_cmd, lark_cmd,
)
from augur.cli_commands.server import mcp_server_cmd, api_cmd, serve_cmd
from augur.cli_commands.monitor import watch_cmd, portfolio_cmd
from augur.cli_commands.meta import skills_cmd, update_cmd, doctor_cmd

for _cmd in (
    analyze_cmd, consensus_cmd, report_cmd, list_personas_cmd,
    fetch_cmd, sentiment_cmd, guidance_cmd,
    workflow_cmd, chat_cmd, committee_cmd,
    backtest_cmd, ic_report_cmd,
    watchlist_add_cmd, watchlist_show_cmd, cron_run_cmd, cron_start_cmd,
    inject_soul_cmd, telegram_cmd, slack_cmd, wechat_cmd, lark_cmd,
    mcp_server_cmd, api_cmd, serve_cmd,
    watch_cmd, portfolio_cmd,
    skills_cmd, update_cmd, doctor_cmd,
):
    main.add_command(_cmd)
del _cmd


if __name__ == "__main__":
    main()
