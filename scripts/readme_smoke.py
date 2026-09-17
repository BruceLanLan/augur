# -*- coding: utf-8 -*-
"""Run the README quickstart / CLI cheat-sheet commands against an installed ``augur``.

Unit tests drive the CLI in-process from the source tree; this script runs the
real console script in a subprocess, so packaging mistakes, removed imports and
wrong defaults that only show up on a fresh install turn CI red.

Everything is offline: a ``sitecustomize`` injected via PYTHONPATH swaps the
market-data provider chain, SEC EDGAR and insider fetches for fixed fakes and
makes every socket connect/DNS lookup fail. A network attempt that the code
under test swallows is still logged and fails the command.

Usage:
    python scripts/readme_smoke.py [path/to/augur]
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

SITECUSTOMIZE = textwrap.dedent('''
    import os
    import socket
    import traceback

    _NET_LOG = os.environ["AUGUR_SMOKE_NET_LOG"]


    def _refuse(what):
        with open(_NET_LOG, "a", encoding="utf-8") as fh:
            fh.write("NETWORK " + what + "\\n")
            traceback.print_stack(file=fh)
        raise OSError("readme_smoke: network disabled (" + what + ")")


    # Loopback is blocked too: with a system proxy configured, requests would
    # reach the internet through a local proxy port.
    def _connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _refuse("connect %r" % (address,))
        return _orig_connect(self, address)


    def _connect_ex(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            _refuse("connect_ex %r" % (address,))
        return _orig_connect_ex(self, address)


    def _getaddrinfo(host, *args, **kwargs):
        _refuse("getaddrinfo %r" % (host,))


    _orig_connect = socket.socket.connect
    _orig_connect_ex = socket.socket.connect_ex
    socket.socket.connect = _connect
    socket.socket.connect_ex = _connect_ex
    socket.getaddrinfo = _getaddrinfo

    def _install_fakes():
        import augur.cli_commands.insider_cmd as _insider_cmd
        import augur.consensus.edgar_fundamentals as _ef
        import augur.data as _data
        import augur.sentiment as _sentiment
        from augur.datasources.base import DataProvider
        from augur.ownership import InsiderTrade

        class _SmokeProvider(DataProvider):
            name = "readme_smoke"

            def fetch(self, ticker):
                # fcf and market_cap are in billions USD, as the real providers return.
                return {"data_source": "readme_smoke", "price": 190.0, "pe": 30.0, "pb": 45.0, "roe": 1.5,
                        "gross_margins": 0.46, "revenue_growth": 0.06, "debt_ratio": 0.8, "fcf": 100.0,
                        "market_cap": 2900.0, "total_debt": 100.0, "total_cash": 60.0}

        _ANNUAL = [
            {"fiscal_year_end": "2025-09-27", "accession": "0000320193-25-000079", "filed": "2025-10-31",
             "metrics": {"revenue": 416.2e9, "net_income": 112.0e9, "gross_margin": 0.469,
                         "operating_income": 133.1e9, "ebitda": 144.7e9, "total_debt": 103.0e9,
                         "total_equity": 73.7e9, "eps_diluted": 7.46}},
            {"fiscal_year_end": "2024-09-28", "accession": "0000320193-24-000123", "filed": "2024-11-01",
             "metrics": {"revenue": 391.0e9, "net_income": 93.7e9, "gross_margin": 0.462,
                         "operating_income": 123.2e9, "ebitda": 134.7e9, "total_debt": 107.6e9,
                         "total_equity": 57.0e9, "eps_diluted": 6.08}},
        ]

        class _FakeEdgarClient:
            def get_cik(self, ticker):
                return 320193

        _data._get_providers = lambda: [_SmokeProvider()]
        _ef.fetch_annual_financials = lambda ticker, years=2: [dict(p) for p in _ANNUAL[:years]]
        _ef._get_client = lambda: _FakeEdgarClient()
        _sentiment._fetch_stocktwits = lambda ticker: (None, 0)
        _insider_cmd._fetch_insider_trades = lambda ticker: [
            InsiderTrade(ticker, "cik%d" % i, "", "2026-09-01", "sell", 1000.0, 200.0, 200000.0) for i in range(3)
        ]


    # site.py only prints a sitecustomize exception and carries on, which would
    # run the commands against unpatched providers.
    try:
        _install_fakes()
    except Exception:
        traceback.print_exc()
        os._exit(97)
''')

Check = Callable[[str], Optional[str]]


def contains(*needles: str) -> Check:
    def check(output: str) -> Optional[str]:
        missing = [n for n in needles if n not in output]
        return "missing %s" % ", ".join(repr(n) for n in missing) if missing else None
    return check


def file_written(pattern: str) -> Check:
    def check(output: str) -> Optional[str]:
        return None if any(Path.cwd().glob(pattern)) else "no file matching %s was written" % pattern
    return check


def fair_value_positive(output: str) -> Optional[str]:
    match = re.search(r"Fair Value/Share:\s*\$(-?[\d,]+\.\d+)", output)
    if not match:
        return "no 'Fair Value/Share' line"
    return None if float(match.group(1).replace(",", "")) > 0 else "fair value is $%s" % match.group(1)


def skill_succeeded(skill_id: str) -> Check:
    return contains("Skill: %s · status: success" % skill_id, "Run ID: run_AAPL_")


# Order matters: research-report, export, dossier and ledger read the runs
# saved by the earlier workflow commands; verify-pack reads the exported pack.
COMMANDS: List[Tuple[Sequence[str], Sequence[Check]]] = [
    (["--version"], [contains("augur, version")]),
    (["analyze", "AAPL"], [contains("Price: 190.00", "AAPL — 18 Masters Consensus", "Signal:")]),
    (["analyze", "NVDA", "--pe", "60", "--roe", "0.45"], [contains("NVDA — 18 Masters Consensus", "Signal:")]),
    (["workflow", "AAPL"], [contains("Price: $190.00", "── Consensus ──", "Run ID: run_AAPL_")]),
    (["research-report", "AAPL"], [contains("## Consensus", "## Disagreement Map", "## Provenance")]),
    (["export", "AAPL", "--format", "md"], [contains("Exported md to run_AAPL_"), file_written("run_AAPL_*_report.md")]),
    (["export", "AAPL", "--format", "evidence-pack", "-o", "pack.zip"],
     [contains("Exported evidence-pack to pack.zip"), file_written("pack.zip")]),
    (["verify-pack", "pack.zip"], [contains("OK: every file matches")]),
    (["committee", "AAPL", "--preset", "value", "-q", "护城河是在变宽还是变窄？"],
     [contains("Investment Committee: AAPL", "source=readme_smoke", "Verdict", "Signal:")]),
    (["valuation", "AAPL"], [contains("DCF Valuation: AAPL", "net debt (debt - cash)"), fair_value_positive]),
    (["dossier", "AAPL"], [contains("Pre-Earnings Dossier: AAPL", "From run run_AAPL_")]),
    (["workflow", "AAPL"], [contains("Run ID: run_AAPL_")]),
    (["ledger", "AAPL"], [contains("Change Ledger: AAPL", "→ run_AAPL_")]),
    (["skill", "list"], [contains("filing-delta", "debt-covenant-review", "insider-cluster-review", "earnings-prep")]),
    (["skill", "run", "filing-delta", "AAPL"], [skill_succeeded("filing-delta")]),
    (["skill", "run", "debt-covenant-review", "AAPL"], [skill_succeeded("debt-covenant-review")]),
    (["skill", "run", "insider-cluster-review", "AAPL"], [skill_succeeded("insider-cluster-review")]),
    (["skill", "run", "earnings-prep", "AAPL"], [skill_succeeded("earnings-prep"), contains("## Consensus")]),
    (["backtest", "AAPL", "--demo", "--days", "30"], [contains("Total records:", "--demo")]),
    (["decisions", "report"], [contains("Decisions:")]),
    (["audit"], [contains("skill_run")]),
]


def resolve_augur(argv: Sequence[str]) -> str:
    if argv:
        path = Path(argv[0])
        if not path.is_file():
            sys.exit("augur executable not found: %s" % path)
        return str(path.absolute())
    found = shutil.which("augur")
    if not found:
        sys.exit("no augur on PATH; pass the executable path as the first argument")
    return found


def main(argv: Sequence[str]) -> int:
    augur = resolve_augur(argv)
    root = Path(tempfile.mkdtemp(prefix="augur_readme_smoke_"))
    shim, home, work = root / "shim", root / "home", root / "work"
    for d in (shim, home, work):
        d.mkdir()
    (shim / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
    net_log = root / "network_attempts.log"

    env = {k: v for k, v in os.environ.items()
           if not k.lower().endswith("_proxy") and not k.startswith(("AUGUR_", "PYTHON"))}
    env.update({
        "HOME": str(home),
        "AUGUR_DATA_DIR": str(root / "data"),
        "AUGUR_SKIP_MACRO_FETCH": "1",
        "AUGUR_EDGAR_CONTACT_EMAIL": "readme-smoke@example.com",
        "AUGUR_SMOKE_NET_LOG": str(net_log),
        "PYTHONPATH": str(shim),
        "PYTHONIOENCODING": "utf-8",
        "NO_COLOR": "1",
        # Clients that bypass Python sockets (yfinance's curl_cffi) still honour
        # proxy variables; point them at a closed port.
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
        "ALL_PROXY": "http://127.0.0.1:9",
        "http_proxy": "http://127.0.0.1:9",
        "https_proxy": "http://127.0.0.1:9",
        "all_proxy": "http://127.0.0.1:9",
    })

    failures = 0
    os.chdir(work)
    for args, checks in COMMANDS:
        label = "augur " + " ".join(args)
        net_log.unlink(missing_ok=True)
        try:
            proc = subprocess.run([augur, *args], cwd=work, env=env, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=300)
        except subprocess.TimeoutExpired:
            print("FAIL  %s  (timed out)" % label)
            failures += 1
            continue
        output = proc.stdout + proc.stderr
        problems = []
        if proc.returncode != 0:
            problems.append("exit code %d" % proc.returncode)
        if not proc.stdout.strip():
            problems.append("empty stdout")
        problems.extend(p for p in (check(output) for check in checks) if p)
        if net_log.exists():
            log = net_log.read_text(encoding="utf-8")
            attempts = sorted({line[len("NETWORK "):] for line in log.splitlines() if line.startswith("NETWORK ")})
            problems.append("network attempted: %s" % "; ".join(attempts[:5]))
            output += "\n--- network attempts ---\n" + log
        if problems:
            failures += 1
            print("FAIL  %s  (%s)" % (label, "; ".join(problems)))
            print(textwrap.indent(output[-4000:], "    | ", lambda line: True))
        else:
            print("PASS  %s" % label)

    print("\n%d/%d commands passed" % (len(COMMANDS) - failures, len(COMMANDS)))
    if failures:
        print("scratch directory kept for inspection: %s" % root)
    else:
        shutil.rmtree(root, ignore_errors=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
