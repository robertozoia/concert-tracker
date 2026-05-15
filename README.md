# Concert Tracker — Ciudad de México

Small personal tool that scrapes upcoming concerts from
[Songkick CDMX](https://www.songkick.com/es/metro-areas/34385-mexico-mexico-city)
once a day, stores them in SQLite, and serves a password-protected web page for
browsing by date with filters for artist and date range.

Tech: FastAPI · SQLAlchemy · SQLite · Jinja2 · plain CSS · HTMX · APScheduler ·
bcrypt + itsdangerous signed cookies.

## Setup

```bash
cp .env.example .env

# Generate a secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate the shared-password hash (run inside a venv with deps installed,
# or inside the container: `docker compose run --rm concerts python -m app.cli hash-password`)
python -m app.cli hash-password
```

Paste both values into `.env`.

## Run with Docker

```bash
docker compose up -d --build
```

On first boot, an empty database triggers a one-time backfill in a background
thread (one HTTP request per listing page, then one per new event — totals
roughly 12 + N for the current ~595 events; throttled at 1–1.5 s between
requests so it takes a few minutes).

After that the daily cron in `app/scheduler.py` fires at `SCRAPE_HOUR` local
(default 04:00 America/Mexico_City). Only genuinely new events trigger a
detail-page fetch — daily runs are cheap.

Logs:

```bash
docker compose logs -f concerts
```

Manual scrape (useful while testing):

```bash
curl -X POST -b "concert_session=$YOUR_COOKIE" http://localhost:8090/admin/scrape
```

## Run locally without Docker

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .

python -m app.cli init-db
python -m app.cli scrape       # one-shot backfill
uvicorn app.main:app --reload --port 8090
```

## Reverse proxy

In your `CaddyFile`:

```
concerts.robertozoia.com {
    reverse_proxy localhost:8090
}
```

## URL structure

- `GET /login` — password form
- `POST /login` — sets `concert_session` cookie (30-day signed token)
- `POST /logout`
- `GET /` — protected event list, server-rendered
- `GET /events?artist=…&start=…&end=…` — HTMX partial used by the filter form
- `POST /admin/scrape` — protected, triggers an immediate scrape, returns stats

## Configuration

See `.env.example`. Notable knobs:

- `END_DATE` — optional upper bound (ISO date). Leave blank to scrape every
  future event Songkick has listed (default). Set e.g. `END_DATE=2026-12-31`
  to cap the window.
- `SCRAPE_HOUR` — local hour for the daily scrape (0–23).
- `SESSION_MAX_AGE` — cookie validity in seconds (default 30 days).

## v1 non-features

- No deletion of past events (rare, low volume, easy to clean up manually).
- No multi-user accounts; one shared password.
- No notifications when new events appear.
- Mexico City only (other metros would just need a different `songkick_metro_path`).
