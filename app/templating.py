from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_WEEKDAYS_ABBR = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
_MONTHS_ABBR = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _weekday_abbr_es(value):
    return _WEEKDAYS_ABBR[value.weekday()]


def _format_date_short_es(value):
    """'vie 15 may 2026' — used by the flat search-result list."""
    return f"{_WEEKDAYS_ABBR[value.weekday()]} {value.day:02d} {_MONTHS_ABBR[value.month]} {value.year}"


templates.env.filters["weekday_abbr_es"] = _weekday_abbr_es
templates.env.filters["date_short_es"] = _format_date_short_es
