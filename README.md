# URL Shortener

A self-hosted URL shortener with click analytics, expiry, rate limiting, and a React frontend — powered by FastAPI, PostgreSQL, and Redis.

---

## Tech stack

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy 2 (asyncpg) · Alembic
- **Cache / rate limiting:** Redis 7
- **Background jobs:** APScheduler (click-count flush, expired-URL cleanup)
- **Frontend:** React 18 · Vite
- **Infra:** Docker Compose · PostgreSQL 16

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose v2)

That is the only hard requirement to run the full stack.

---

## Quick start

```bash
git clone https://github.com/davidbarcut24/url-shortener.git
cd url-shortener
cp .env.example .env          # review and edit values before going to production
docker compose up --build
```

| Service  | URL                    |
|----------|------------------------|
| Frontend | http://localhost:5173  |
| API      | http://localhost:8000  |
| API docs | http://localhost:8000/docs |

Stop everything with `docker compose down`. Add `-v` to also remove the Postgres volume.

---

## Running tests

Tests run against SQLite (via `aiosqlite`) and `fakeredis` — no running services needed.

```bash
pip install -r requirements.txt
pytest
```

`pytest.ini` sets `asyncio_mode = auto` so every async test is discovered automatically.

---

## API reference

All API routes are prefixed with `/api` except the redirect route.

### POST /api/shorten

Create a shortened URL.

**Request body**

```json
{
  "url": "https://example.com/very/long/path",
  "expires_in_days": 7,
  "custom_code": "mylink"
}
```

| Field            | Type          | Required | Description                                    |
|------------------|---------------|----------|------------------------------------------------|
| `url`            | string        | yes      | Destination URL (http/https, max 2048 chars)   |
| `expires_in_days`| integer       | no       | Days until the link expires (omit = never)     |
| `custom_code`    | string        | no       | Alphanumeric slug, 1–10 chars                  |

**Response `201`**

```json
{
  "short_code": "mylink",
  "short_url": "http://localhost:8000/mylink",
  "original_url": "https://example.com/very/long/path",
  "expires_at": "2026-04-24T00:00:00"
}
```

---

### GET /{code}

Redirect to the original URL (`302`). Returns `404` if the code is unknown, `410` if expired, `429` if rate-limited.

---

### DELETE /api/url/{code}

Delete a short URL immediately. Returns `204 No Content` on success, `404` if not found.

---

### GET /api/analytics/{code}

Retrieve click statistics for a short URL.

**Response `200`**

```json
{
  "short_code": "mylink",
  "original_url": "https://example.com/very/long/path",
  "click_count": 42,
  "created_at": "2026-04-17T10:00:00",
  "expires_at": "2026-04-24T00:00:00"
}
```

---

## Environment variables

Copy `.env.example` to `.env` and adjust as needed. Docker Compose reads `.env` automatically.

| Variable              | Default                                                    | Description                                                  |
|-----------------------|------------------------------------------------------------|--------------------------------------------------------------|
| `DATABASE_URL`        | `postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener` | SQLAlchemy async database URL |
| `REDIS_URL`           | `redis://localhost:6379`                                   | Redis connection URL                                         |
| `BASE_URL`            | `http://localhost:8000`                                    | Public base URL prepended to generated short URLs            |
| `ALLOWED_ORIGINS`     | `http://localhost:5173`                                    | Comma-separated CORS origins                                 |
| `IP_HASH_SALT`        | `CHANGE_ME_IN_PRODUCTION`                                  | HMAC secret for hashing visitor IPs before storage. **Change this before deploying.** |
| `SHORT_CODE_LENGTH`   | `7`                                                        | Character length of auto-generated short codes               |
| `DEFAULT_CACHE_TTL`   | `86400`                                                    | Redis TTL for cached URL entries (seconds)                   |
| `RATE_LIMIT_SHORTEN`  | `10`                                                       | Max shorten requests per IP per window                       |
| `RATE_LIMIT_REDIRECT` | `60`                                                       | Max redirect requests per IP per window                      |
| `RATE_LIMIT_WINDOW`   | `60`                                                       | Rate-limit sliding window size (seconds)                     |
| `DB_POOL_SIZE`        | `5`                                                        | SQLAlchemy connection pool size                              |
| `DB_MAX_OVERFLOW`     | `10`                                                       | Max connections above pool size                              |

---

## Architecture

```
React/Vite (port 5173)
       |
       | HTTP
       v
FastAPI (port 8000)
  ├── POST /api/shorten   — validates + persists URL, returns short code
  ├── GET  /{code}        — checks Redis cache, falls back to Postgres, 302 redirect
  ├── DELETE /api/url/{code}
  └── GET  /api/analytics/{code}
       |                         |
  asyncpg (PostgreSQL)      Redis
  persistent storage        - URL cache (TTL-based)
                            - Click-count write buffer
                            - Rate-limit counters

APScheduler (in-process)
  ├── every 60 s  — flush buffered click counts from Redis to Postgres
  └── every 1 h   — delete expired URL rows from Postgres
```

Click counts are written to Redis first and flushed to Postgres in batches every 60 seconds, keeping the hot redirect path free of synchronous DB writes.
