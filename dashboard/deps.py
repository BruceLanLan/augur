"""Shared dependencies for dashboard route modules.

Provides the Jinja2 templates object so route modules can render HTML
without importing from app.py (which would create a circular import).
"""

from pathlib import Path

try:
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
except ImportError:
    templates = None  # type: ignore[assignment]
