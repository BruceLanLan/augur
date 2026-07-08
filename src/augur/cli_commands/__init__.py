# -*- coding: utf-8 -*-
"""
augur.cli_commands - Click command modules, wired into augur.cli's ``main`` group.

Each module here defines its own bare ``@click.command(...)`` functions
(mirroring how ``dashboard/routes/*.py`` each define their own ``APIRouter``);
``augur.cli`` imports every command and registers it onto ``main`` via
``main.add_command(...)``, the click equivalent of ``app.include_router(...)``.
"""
