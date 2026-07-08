# -*- coding: utf-8 -*-
"""augur.cli_commands.meta - skills / update"""

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
