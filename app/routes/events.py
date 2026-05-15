from __future__ import annotations

from datetime import date
from itertools import groupby
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_auth
from ..config import settings
from ..db import get_session
from ..models import Event
from ..scraper import scrape_all
from ..templating import templates

router = APIRouter()

_MONTH_LABEL_ES = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _query_events(
    session: Session,
    *,
    artist: str | None,
    start: date | None,
    end: date | None,
) -> list[Event]:
    stmt = select(Event)
    effective_start = start or date.today()
    stmt = stmt.where(Event.event_date >= effective_start)
    if end is not None:
        stmt = stmt.where(Event.event_date <= end)
    if artist:
        stmt = stmt.where(Event.artist.ilike(f"%{artist}%"))
    stmt = stmt.order_by(Event.event_date.asc(), Event.artist.asc())
    return list(session.execute(stmt).scalars())


def _group_by_month(events: list[Event]) -> list[dict]:
    """Returns [{year, month, label, anchor, count, events}] in chronological order."""
    groups = []
    for (year, month), items in groupby(events, key=lambda e: (e.event_date.year, e.event_date.month)):
        bucket = list(items)
        groups.append(
            {
                "year": year,
                "month": month,
                "label": f"{_MONTH_LABEL_ES[month]} {year}",
                "anchor": f"month-{year:04d}-{month:02d}",
                "count": len(bucket),
                "events": bucket,
            }
        )
    return groups


def _load_view_context(
    session: Session,
    *,
    artist: str | None,
    start: str | None,
    end: str | None,
) -> tuple[list[Event], list[dict], date | None]:
    start_d = _parse_date(start)
    end_d = _parse_date(end) or settings.resolved_end_date()
    events = _query_events(session, artist=artist, start=start_d, end=end_d)
    return events, _group_by_month(events), end_d


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    _auth: Annotated[bool, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
    artist: str | None = None,
    start: str | None = None,
    end: str | None = None,
):
    events, months, end_d = _load_view_context(session, artist=artist, start=start, end=end)
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "months": months,
            "events": events,
            "artist": artist or "",
            "start": start or "",
            "end": end_d.isoformat() if end_d else "",
            "total": len(events),
        },
    )


@router.get("/events", response_class=HTMLResponse)
def events_partial(
    request: Request,
    _auth: Annotated[bool, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
    artist: str | None = None,
    start: str | None = None,
    end: str | None = None,
):
    events, months, _ = _load_view_context(session, artist=artist, start=start, end=end)
    return templates.TemplateResponse(
        request,
        "partials/event_list.html",
        {
            "months": months,
            "events": events,
            "artist": artist or "",
            "total": len(events),
        },
    )


@router.post("/admin/scrape")
def admin_scrape(
    _auth: Annotated[bool, Depends(require_auth)],
    session: Annotated[Session, Depends(get_session)],
):
    stats = scrape_all(session=session)
    return JSONResponse(stats.to_dict())
