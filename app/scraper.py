from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal
from .models import Event

logger = logging.getLogger(__name__)

_CONCERT_ID_RE = re.compile(r"/concerts/(\d+)-")
_LIST_PARSER = "lxml"
_DETAIL_DELAY_SEC = 1.5
_LIST_DELAY_SEC = 1.0
_MAX_PAGES = 50  # safety cap


@dataclass
class ParsedEvent:
    songkick_id: str
    artist: str
    event_date: date
    venue: str
    songkick_url: str


@dataclass
class ScrapeStats:
    pages_fetched: int = 0
    events_seen: int = 0
    new_events: int = 0
    detail_fetches: int = 0
    detail_errors: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "pages_fetched": self.pages_fetched,
            "events_seen": self.events_seen,
            "new_events": self.new_events,
            "detail_fetches": self.detail_fetches,
            "detail_errors": self.detail_errors,
            "errors": self.errors,
        }


def _headers() -> dict[str, str]:
    return {
        "User-Agent": settings.user_agent,
        "Accept-Language": "es,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml",
    }


def _fetch(url: str, *, timeout: int = 20) -> str:
    response = requests.get(url, headers=_headers(), timeout=timeout)
    response.raise_for_status()
    return response.text


def _parse_listing(html: str) -> list[ParsedEvent]:
    soup = BeautifulSoup(html, _LIST_PARSER)
    out: list[ParsedEvent] = []
    for li in soup.select("li.event-listings-element"):
        time_el = li.select_one("time[datetime]")
        if not time_el:
            continue
        dt_str = time_el.get("datetime", "")
        try:
            event_dt = datetime.fromisoformat(dt_str)
        except ValueError:
            continue
        ev_date = event_dt.date()

        link = li.select_one("a.event-link[href*='/concerts/']") or li.select_one(
            "a.thumb[href*='/concerts/']"
        )
        if not link:
            continue
        href = link.get("href", "")
        m = _CONCERT_ID_RE.search(href)
        if not m:
            continue
        songkick_id = m.group(1)
        songkick_url = urljoin(settings.songkick_base_url, href.split("?")[0])

        artist_el = li.select_one("p.artists strong")
        artist = artist_el.get_text(strip=True) if artist_el else ""
        if not artist:
            link_span = link.select_one("strong") or link.select_one("span")
            artist = link_span.get_text(strip=True) if link_span else ""

        venue_el = li.select_one("a.venue-link")
        venue = venue_el.get_text(strip=True) if venue_el else ""

        if not artist:
            continue

        out.append(
            ParsedEvent(
                songkick_id=songkick_id,
                artist=artist,
                event_date=ev_date,
                venue=venue,
                songkick_url=songkick_url,
            )
        )
    return out


def _parse_ticket_url(html: str) -> str | None:
    soup = BeautifulSoup(html, _LIST_PARSER)
    el = soup.select_one("a.buy-ticket-link[href]") or soup.select_one(
        "a.buy-button[href]"
    )
    if not el:
        return None
    href = el.get("href", "")
    if not href:
        return None
    return urljoin(settings.songkick_base_url, href)


def scrape_all(session: Session | None = None) -> ScrapeStats:
    """Scrape Songkick metro page; upsert events; enrich new events with ticket URL.

    Stops paginating when (a) the page returns no events, or (b) every event on
    the page is past the configured END_DATE.
    """
    stats = ScrapeStats()
    end_date = settings.resolved_end_date()
    own_session = session is None
    if session is None:
        session = SessionLocal()

    try:
        for page in range(1, _MAX_PAGES + 1):
            url = (
                f"{settings.songkick_base_url}{settings.songkick_metro_path}?page={page}"
            )
            logger.info("Fetching listing page %s", page)
            try:
                html = _fetch(url)
            except requests.RequestException as exc:
                stats.errors.append(f"page {page}: {exc}")
                logger.warning("Listing fetch failed page=%s: %s", page, exc)
                break
            stats.pages_fetched += 1

            events = _parse_listing(html)
            if not events:
                logger.info("No events on page %s; stopping", page)
                break

            stats.events_seen += len(events)
            if end_date is None:
                in_window = events
                stop_after = False
            else:
                in_window = [e for e in events if e.event_date <= end_date]
                stop_after = len(in_window) < len(events)

            for parsed in in_window:
                _upsert(session, parsed, stats)

            session.commit()

            if stop_after:
                logger.info(
                    "Reached events past END_DATE %s on page %s; stopping", end_date, page
                )
                break

            time.sleep(_LIST_DELAY_SEC)
        return stats
    finally:
        if own_session:
            session.close()


def _upsert(session: Session, parsed: ParsedEvent, stats: ScrapeStats) -> None:
    existing = session.execute(
        select(Event).where(Event.songkick_id == parsed.songkick_id)
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if existing is not None:
        existing.last_seen_at = now
        existing.artist = parsed.artist
        existing.event_date = parsed.event_date
        existing.venue = parsed.venue
        existing.songkick_url = parsed.songkick_url
        return

    ticket_url: str | None = None
    try:
        detail_html = _fetch(parsed.songkick_url)
        stats.detail_fetches += 1
        ticket_url = _parse_ticket_url(detail_html)
    except requests.RequestException as exc:
        stats.detail_errors += 1
        stats.errors.append(f"detail {parsed.songkick_id}: {exc}")
        logger.warning("Detail fetch failed id=%s: %s", parsed.songkick_id, exc)
    finally:
        time.sleep(_DETAIL_DELAY_SEC)

    event = Event(
        songkick_id=parsed.songkick_id,
        artist=parsed.artist,
        event_date=parsed.event_date,
        venue=parsed.venue,
        songkick_url=parsed.songkick_url,
        ticket_url=ticket_url,
        created_at=now,
        last_seen_at=now,
    )
    session.add(event)
    stats.new_events += 1
