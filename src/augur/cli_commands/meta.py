# -*- coding: utf-8 -*-
"""augur.cli_commands.meta - skills / update / doctor"""

import click

from augur import __version__


@click.command("skills")
@click.option("--school", default=None, help="Filter by school (value/growth/macro/china)")
@click.option("--lang", default=None, help="Filter by language (en/zh)")
def skills_cmd(school, lang):
    """List available Augur skill profiles.

    \b
    Examples:
      augur skills                        # Show all skills
      augur skills --school value         # Value investing skills only
      augur skills --lang zh              # Chinese-language skills only
      augur skills --school growth --lang en
    """
    import re as _re
    import yaml as _yaml
    from pathlib import Path as _Path

    # augur/ and skills/ are always sibling packages one level up from
    # wherever augur/ itself lives -- "src/" in a dev checkout,
    # "site-packages/" in a real pip install -- so walking up from this
    # file (cli_commands/meta.py -> cli_commands -> augur -> that shared
    # parent) resolves correctly in both.
    skills_dir = _Path(__file__).resolve().parents[2] / "skills"

    if not skills_dir.exists():
        click.echo(
            "Skills directory not found.\n"
            "  Hint: Run generate_skills.py or check your augur installation.",
            err=True,
        )
        raise SystemExit(1)

    skill_files = sorted(skills_dir.glob("*/SKILL.md"))
    if not skill_files:
        click.echo("No SKILL.md files found in skills/.")
        return

    rows = []
    for path in skill_files:
        try:
            content = path.read_text(encoding="utf-8")
            # Extract YAML frontmatter between --- delimiters
            m = _re.match(r"^---\n(.*?)\n---", content, _re.DOTALL)
            if not m:
                continue
            data = _yaml.safe_load(m.group(1)) or {}
            augur_meta = data.get("metadata", {}).get("augur", {})
            skill_school = augur_meta.get("school", "")
            skill_lang = augur_meta.get("language", "")
            skill_name = data.get("name", path.parent.name)
            skill_desc = data.get("description", "")

            if school and skill_school.lower() != school.lower():
                continue
            if lang and skill_lang.lower() != lang.lower():
                continue

            rows.append((skill_name, skill_desc, skill_lang, skill_school))
        except Exception:
            continue

    if not rows:
        click.echo("No skills match the given filters.")
        return

    # Print formatted table
    click.echo(f"\nAugur Skills ({len(rows)} found)\n")
    header = f"{'Name':<30s} {'Language':<10s} {'School':<10s} {'Description'}"
    click.echo(header)
    click.echo("-" * 90)
    for name, desc, skill_lang_val, skill_school_val in rows:
        # Truncate description for table fit
        short_desc = desc[:45] + "..." if len(desc) > 45 else desc
        click.echo(f"{name:<30s} {skill_lang_val:<10s} {skill_school_val:<10s} {short_desc}")


@click.command("update")
def update_cmd():
    """Update Augur to the latest version from the repository.

    \b
    Examples:
      augur update          # Pull latest changes and reinstall
    """
    import subprocess
    import sys
    from pathlib import Path

    # cli_commands/meta.py -> cli_commands -> augur -> src -> repo root
    repo_root = Path(__file__).resolve().parents[3]

    click.echo(f"🦉 Augur {__version__} → checking for updates…")

    # Verify this is a git repo
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        click.echo(
            "⚠  This installation is not a git clone.\n"
            "   To update: git clone https://github.com/BruceLanLan/augur.git",
            err=True,
        )
        raise SystemExit(1)

    # Check for uncommitted changes that would block pull
    status = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain"],
        capture_output=True, text=True,
    )
    if status.returncode != 0:
        click.echo(f"⚠  git status failed: {status.stderr.strip()}", err=True)
        raise SystemExit(1)

    if status.stdout.strip():
        click.echo(
            "⚠  Working tree has uncommitted changes — aborting to avoid conflicts.\n"
            "   Stash or commit your changes first: git stash",
            err=True,
        )
        raise SystemExit(1)

    # Pull
    click.echo("   Pulling latest changes…")
    pull = subprocess.run(
        ["git", "-C", str(repo_root), "pull", "--ff-only"],
        capture_output=True, text=True,
    )
    if pull.returncode != 0:
        click.echo(f"⚠  git pull failed:\n{pull.stderr.strip()}", err=True)
        raise SystemExit(1)

    if "Already up to date" in pull.stdout:
        click.echo(f"✅ Already up to date ({__version__}).")
        return

    click.echo(pull.stdout.strip())

    # Reinstall
    click.echo("   Reinstalling package…")
    pip = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    if pip.returncode != 0:
        click.echo(f"⚠  pip install failed:\n{pip.stderr.strip()}", err=True)
        raise SystemExit(1)

    # Re-import to get new version
    try:
        import importlib
        import augur as _augur_mod
        importlib.reload(_augur_mod)
        new_version = _augur_mod.__version__
    except Exception:
        new_version = "unknown"

    click.echo(f"✅ Updated to {new_version}.")


@click.command("doctor")
@click.option(
    "--offline", is_flag=True, default=False,
    help="Skip live data-source connectivity checks (env/config checks only, no network calls)",
)
def doctor_cmd(offline):
    """Diagnose common local environment issues.

    Checks the Python/SSL toolchain for a known-bad combination that silently
    breaks yfinance (a macOS CommandLineTools Python linked against LibreSSL
    instead of real OpenSSL causes curl_cffi to raise SSLError), reports which
    optional API keys are configured, probes the configured data-source chain
    for real connectivity, and shows how much learning-engine outcome data has
    accumulated.

    \b
    Examples:
      augur doctor              # Full diagnostic, including live network checks
      augur doctor --offline    # Environment/config checks only, no network calls
    """
    import os
    import ssl
    import sys

    click.echo("\n🦉 Augur Doctor\n")

    # -- Python / SSL toolchain --
    click.echo("Python environment:")
    click.echo(f"  Python:      {sys.version.split()[0]}  ({sys.executable})")
    openssl_version = ssl.OPENSSL_VERSION
    click.echo(f"  SSL backend: {openssl_version}")
    if "LibreSSL" in openssl_version:
        click.echo(
            "  ⚠  LibreSSL detected. yfinance's curl_cffi backend needs real OpenSSL and\n"
            "     will fail with SSLError on LibreSSL -- this combination commonly happens\n"
            "     when a venv is built from macOS's bundled CommandLineTools Python.\n"
            "     Fix: rebuild the venv with a Python linked against real OpenSSL, e.g.\n"
            "       brew install python@3.12 && /opt/homebrew/bin/python3.12 -m venv .venv"
        )
    else:
        click.echo("  ✅ OpenSSL backend looks fine for yfinance/curl_cffi.")

    # -- Optional API keys --
    click.echo("\nAPI key configuration:")
    for env_name, desc in (
        ("FINNHUB_API_KEY", "Finnhub fallback market data (free tier: 60 req/min)"),
        ("ALPHAVANTAGE_API_KEY", "Alpha Vantage fallback fundamentals (free tier: 25 req/day)"),
        ("OPENAI_API_KEY", "LLM features (chat personas, EDGAR guidance extraction)"),
        ("AUGUR_EDGAR_CONTACT_EMAIL", "SEC EDGAR contact email (required by SEC fair-use policy)"),
    ):
        configured = bool(os.environ.get(env_name, "").strip())
        mark = "✅" if configured else "⚪"
        state = "configured" if configured else "not set"
        click.echo(f"  {mark} {env_name:<26s} {state:<12s} — {desc}")

    # -- Data source chain connectivity --
    click.echo("\nData sources:")
    try:
        from augur.datasources import default_providers
        providers = default_providers()
    except Exception as e:
        providers = []
        click.echo(f"  ⚠  Could not load data source chain: {e}")

    if offline:
        for p in providers:
            click.echo(f"  ⚪ {p.name:<14s} skipped (--offline)")
    else:
        for p in providers:
            try:
                p.fetch("AAPL")
                click.echo(f"  ✅ {p.name:<14s} reachable")
            except Exception as e:
                click.echo(f"  ❌ {p.name:<14s} FAILED — {str(e)[:100]}")

    # -- Learning engine data accumulation --
    click.echo("\nLearning engine (outcome data for probability calibration):")
    try:
        from augur.registry import _get_learning_engine
        le = _get_learning_engine()
        total = le.prediction_count
        pending = le.pending_count
        resolved = total - pending
        click.echo(f"  Predictions: {total} total, {resolved} resolved, {pending} pending")
        last_res = le.last_resolution
        if last_res:
            import datetime as _dt
            ts = _dt.datetime.fromtimestamp(last_res["timestamp"]).strftime("%Y-%m-%d %H:%M")
            click.echo(
                f"  Last resolution sweep: {ts} "
                f"({last_res['resolved']} resolved, {last_res['failed']} failed)"
            )
        else:
            click.echo("  Last resolution sweep: never run")
    except Exception as e:
        click.echo(f"  ⚠  Could not read learning engine state: {e}")

    click.echo()
