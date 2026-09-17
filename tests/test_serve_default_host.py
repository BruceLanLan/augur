# -*- coding: utf-8 -*-
"""`augur serve` / `augur api` bind to loopback unless told otherwise.

Both used to default to 0.0.0.0 while auth is only active when
AUGUR_API_TOKEN (or multi-user mode) is configured, so following the README
exposed the dashboard's write endpoints to the whole local network. Docker
and docker-compose pass --host 0.0.0.0 explicitly and are unaffected.
"""
from unittest.mock import patch

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def no_token(monkeypatch):
    monkeypatch.delenv("AUGUR_API_TOKEN", raising=False)
    monkeypatch.delenv("AUGUR_MULTI_USER", raising=False)


def _serve(*args):
    from augur.cli_commands.server import serve_cmd

    with patch("uvicorn.run") as run:
        result = CliRunner().invoke(serve_cmd, list(args))
    return result, run


def test_serve_defaults_to_loopback():
    result, run = _serve()

    assert result.exit_code == 0, result.output
    assert run.call_args.kwargs["host"] == "127.0.0.1"
    assert "WARNING" not in result.output


def test_serve_warns_when_exposed_without_auth():
    result, run = _serve("--host", "0.0.0.0")

    assert result.exit_code == 0, result.output
    assert run.call_args.kwargs["host"] == "0.0.0.0"
    assert "WARNING" in result.output
    assert "AUGUR_API_TOKEN" in result.output


def test_serve_does_not_warn_when_token_configured(monkeypatch):
    monkeypatch.setenv("AUGUR_API_TOKEN", "x" * 32)
    result, _ = _serve("--host", "0.0.0.0")

    assert "WARNING" not in result.output


def test_api_defaults_to_loopback_and_warns_when_exposed():
    from augur.cli_commands.server import api_cmd

    with patch("uvicorn.run") as run:
        default = CliRunner().invoke(api_cmd, [])
        exposed = CliRunner().invoke(api_cmd, ["--host", "0.0.0.0"])

    assert run.call_args_list[0].kwargs["host"] == "127.0.0.1"
    assert "WARNING" not in default.output
    assert "WARNING" in exposed.output
