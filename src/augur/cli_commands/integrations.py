# -*- coding: utf-8 -*-
"""augur.cli_commands.integrations - telegram / slack / wechat / lark / inject-soul"""

import click


@click.command("inject-soul")
@click.option("--profile", "-p", required=True, help="Profile name to create")
@click.option("--persona", required=True, help="Persona ID to inject (e.g. buffett, duan_yongping)")
@click.option("--output-dir", "-o", default=None, help="Output directory (default: current dir)")
@click.option("--format", "-f", "fmt", type=click.Choice(["hermes", "claude", "raw"]), default="hermes", help="Output format")
def inject_soul_cmd(profile, persona, output_dir, fmt):
    """Inject persona soul into a profile config file"""
    from augur.soul import inject_soul

    try:
        result_path = inject_soul(profile, persona, format=fmt, output_dir=output_dir)
        click.echo(f"Soul injected: {result_path}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@click.command("telegram")
def telegram_cmd():
    """Start the Telegram bot"""
    from augur.optional_deps import require_optional
    try:
        require_optional("telegram", "Telegram bot integration", "pip install 'augur-agents[telegram]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.telegram_bot import run_telegram_bot
    run_telegram_bot()


@click.command("slack")
@click.option("--mode", type=click.Choice(["socket", "http"]), default="socket",
              help="Mode: socket (dev) or http (production)")
@click.option("--port", type=int, default=3000, help="Port for HTTP mode")
def slack_cmd(mode, port):
    """Start the Slack bot"""
    from augur.optional_deps import require_optional
    try:
        require_optional("slack_bolt", "Slack bot integration", "pip install 'augur-agents[slack]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.slack_bot import run_slack_bot
    run_slack_bot(mode=mode, port=port)


@click.command("wechat")
@click.option("--mode", type=click.Choice(["personal", "wecom", "webhook"]), default="personal",
              help="Mode: personal (GeWeChat), wecom (enterprise), or webhook (push only)")
@click.option("--port", type=int, default=8066, help="Port for callback server")
def wechat_cmd(mode, port):
    """Start the WeChat bot (personal/wecom/webhook)"""
    from augur.optional_deps import require_optional
    try:
        require_optional("augur.bots.wechat_bot", "WeChat bot integration", "pip install 'augur-agents[wechat]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.wechat_bot import run_wechat_bot
    run_wechat_bot(mode=mode, port=port)


@click.command("lark")
@click.option("--mode", type=click.Choice(["event", "webhook"]), default="event",
              help="Mode: event (subscription) or webhook (push only)")
@click.option("--port", type=int, default=9000, help="Port for event server")
def lark_cmd(mode, port):
    """Start the Lark/Feishu bot"""
    from augur.optional_deps import require_optional
    try:
        require_optional("augur.bots.lark_bot", "Lark/Feishu bot integration", "pip install 'augur-agents[lark]'")
    except ImportError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    from augur.bots.lark_bot import run_lark_bot
    run_lark_bot(mode=mode, port_num=port)
