# -*- coding: utf-8 -*-
"""augur.cli_commands.server - mcp-server / api / serve"""

import click


@click.command("mcp-server")
def mcp_server_cmd():
    """Start the MCP server (stdio mode)"""
    from augur.mcp_server import run_server
    run_server()


@click.command("api")
@click.option("--port", type=int, default=8900, help="Port to run on")
@click.option("--host", default="0.0.0.0", help="Host to bind to")
def api_cmd(port, host):
    """Start the REST API server"""
    try:
        import uvicorn
        from augur.api import app
        click.echo(f"Starting Augur API on {host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except ImportError:
        click.echo(
            "Error: uvicorn and fastapi are not installed.\n"
            "  Install with: pip install 'augur-agents[api]' (or: pip install fastapi uvicorn)\n"
            "  CLI commands (analyze, consensus) still work without the API server.",
            err=True,
        )
        raise SystemExit(1)


@click.command("serve")
@click.option("--port", default=8000, show_default=True, help="Dashboard port")
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind host")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open browser on start")
def serve_cmd(port, host, open_browser):
    """Start the Augur web dashboard.

    \b
    Examples:
      augur serve                       # Start on default port 8000
      augur serve --port 8080           # Custom port
      augur serve --open                # Open browser automatically
    """
    import sys
    from pathlib import Path as _Path

    # Resolve dashboard app path relative to this file. augur/ and dashboard/
    # are always sibling packages one level up from wherever augur/ itself
    # lives -- "src/" in a dev checkout, "site-packages/" in a real pip
    # install -- so walking up from this file (cli_commands/server.py ->
    # cli_commands -> augur -> that shared parent) resolves correctly in
    # both, unlike a repo-root-relative path (which only worked by
    # incidentally having the repo root on sys.path in dev/test runs).
    dashboard_dir = _Path(__file__).resolve().parents[2] / "dashboard"
    if str(dashboard_dir) not in sys.path:
        sys.path.insert(0, str(dashboard_dir.parent))

    try:
        import uvicorn
    except ImportError:
        click.echo(
            "Error: uvicorn is not installed.\n"
            "  Install with: pip install uvicorn\n"
            "  Or run manually: python3 -m dashboard.app",
            err=True,
        )
        raise SystemExit(1)

    try:
        from dashboard.app import app as dashboard_app
    except ImportError as e:
        click.echo(
            f"Error: Could not import dashboard app: {e}\n"
            "  Run manually: python3 -m dashboard.app",
            err=True,
        )
        raise SystemExit(1)

    click.echo(f"\U0001f989 Augur Dashboard starting at http://localhost:{port}")

    if open_browser:
        import threading
        import webbrowser

        def _open():
            webbrowser.open(f"http://localhost:{port}")

        threading.Timer(1.0, _open).start()

    uvicorn.run(dashboard_app, host=host, port=port)
