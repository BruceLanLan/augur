# -*- coding: utf-8 -*-
"""v10.15: Primary codepaths must not import legacy scanner/ package."""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Optional legacy modules not yet migrated to augur.*
ALLOWED_SCANNER_IMPORTS: dict[str, set[str]] = {
    "src/augur/registry.py": {"scanner.ten_x_screener"},
    "src/augur/consensus/engine.py": {"scanner.ten_x_screener"},
}

_SCANNER_IMPORT_RE = re.compile(
    r"""(?:^|\s)(?:from\s+scanner(?:\.\w+)*\s+import|import\s+scanner(?:\.\w+)*)""",
    re.MULTILINE,
)


def _iter_primary_python_files() -> list[Path]:
    files = [REPO_ROOT / "src" / "dashboard" / "app.py"]
    files.extend(sorted((REPO_ROOT / "src" / "augur").rglob("*.py")))
    return files


def _scanner_modules_in_file(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    modules: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "scanner" not in stripped:
            continue
        if not _SCANNER_IMPORT_RE.search(stripped):
            continue
        if stripped.startswith("from scanner."):
            mod = stripped.split("import", 1)[0].replace("from", "").strip()
            modules.add(mod)
        elif stripped.startswith("import scanner"):
            modules.add("scanner")
    return modules


@pytest.mark.parametrize("rel_path", [p.relative_to(REPO_ROOT).as_posix() for p in _iter_primary_python_files()])
def test_no_scanner_imports_in_primary_codepath(rel_path: str):
    path = REPO_ROOT / rel_path
    found = _scanner_modules_in_file(path)
    allowed = ALLOWED_SCANNER_IMPORTS.get(rel_path, set())
    unexpected = found - allowed
    assert not unexpected, (
        f"{rel_path} imports legacy scanner package: {sorted(unexpected)}. "
        "Use augur.* instead (see scanner/README.md)."
    )


def test_dashboard_uses_augur_registry_directly():
    text = (REPO_ROOT / "src" / "dashboard" / "app.py").read_text(encoding="utf-8")
    assert "from augur.registry import AgentRegistry, DecisionCoordinator" in text
    assert "from augur.personas.base import MarketContext" in text
    assert "from scanner." not in text
    assert "import scanner" not in text
