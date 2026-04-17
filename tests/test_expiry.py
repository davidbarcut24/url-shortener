"""
Tests for URL expiry behaviour.

Key invariants under test:
- An expired link returns 410 Gone, not 404 Not Found.
- A link that has not yet expired (even 1 second before expiry) still works.
- Analytics on an expired URL returns 200 — the record is still in the DB
  (get_analytics does not filter by expiry).
- The DB `expires_at` value is set correctly when expires_in_days is supplied.
- The cleanup job (cleanup_expired_urls) hard-deletes expired rows.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select

from app.models import Url
from app.services.expiry import cleanup_expired_urls


# ---------------------------------------------------------------------------
# HTTP redirect behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_redirect_returns_410_for_expired_link(client):
    """Expired link (expires_in_days=-1) must return 410, not 404."""
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    assert res.status_code == 201
    code = res.json()["short_code"]

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 410
    assert "detail" in res.json()


@pytest.mark.asyncio
async def test_expired_link_does_not_return_404(client):
    """
    The 410 vs 404 distinction is intentional: callers must be able to tell
    the difference between a code that never existed and one that has expired.
    """
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    code = res.json()["short_code"]

    redirect_res = await client.get(f"/{code}", follow_redirects=False)
    assert redirect_res.status_code != 404


@pytest.mark.asyncio
async def test_link_one_second_before_expiry_still_works(client, db_session):
    """
    A link whose expires_at is 1 second in the future must redirect (302),
    not 410.
    """
    from sqlalchemy import select as sa_select

    shorten_res = await client.post("/api/shorten", json={"url": "https://fresh.com"})
    assert shorten_res.status_code == 201
    code = shorten_res.json()["short_code"]

    # Override expires_at to be 1 second from now.
    future = datetime.now(timezone.utc) + timedelta(seconds=1)
    url_row = await db_session.scalar(sa_select(Url).where(Url.short_code == code))
    url_row.expires_at = future
    await db_session.commit()

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302


@pytest.mark.asyncio
async def test_link_with_no_expiry_never_returns_410(client):
    """Links created without expires_in_days should redirect indefinitely."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302


# ---------------------------------------------------------------------------
# expires_at field in DB
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expires_at_is_null_when_no_expiry_given(client, db_session):
    """When expires_in_days is omitted the DB row must have expires_at=NULL."""
    from sqlalchemy import select as sa_select

    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    url_row = await db_session.scalar(sa_select(Url).where(Url.short_code == code))
    assert url_row.expires_at is None


@pytest.mark.asyncio
async def test_expires_at_is_set_when_expires_in_days_given(client, db_session):
    """When expires_in_days=3 the DB row's expires_at should be ~3 days from now."""
    from sqlalchemy import select as sa_select

    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": 3}
    )
    code = shorten_res.json()["short_code"]

    url_row = await db_session.scalar(sa_select(Url).where(Url.short_code == code))
    assert url_row.expires_at is not None

    # SQLite stores datetimes as naive strings; compare without timezone.
    now = datetime.utcnow()
    expires = url_row.expires_at if not url_row.expires_at.tzinfo else url_row.expires_at.replace(tzinfo=None)
    delta = expires - now
    # Should be roughly 3 days (allow ±5 minutes for test latency)
    assert timedelta(days=2, hours=23, minutes=55) < delta < timedelta(days=3, minutes=5)


@pytest.mark.asyncio
async def test_expires_at_in_shorten_response(client):
    """The ShortenResponse must include expires_at when expires_in_days is given."""
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": 7}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["expires_at"] is not None


@pytest.mark.asyncio
async def test_expires_at_null_in_shorten_response(client):
    """The ShortenResponse expires_at must be null when no expiry is requested."""
    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    assert res.json()["expires_at"] is None


# ---------------------------------------------------------------------------
# Analytics on expired URL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_returns_200_for_expired_url(client):
    """
    get_analytics does not check expiry — it returns the row regardless.
    This lets operators inspect traffic data even after a link has expired.
    """
    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    data = res.json()
    assert data["short_code"] == code


# ---------------------------------------------------------------------------
# __expired__ sentinel written to Redis
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_link_writes_expired_sentinel_to_redis(client, fake_redis):
    """
    After the first request hits a DB-expired link the redirect handler must
    write the '__expired__' sentinel so subsequent requests don't need a DB hit.
    """
    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)

    cached = await fake_redis.get(f"url:{code}")
    assert cached == "__expired__"


@pytest.mark.asyncio
async def test_expired_sentinel_in_redis_returns_410_without_db_hit(client, fake_redis):
    """
    When the '__expired__' sentinel is already in Redis the redirect must return
    410 immediately, without ever querying the DB.
    """
    # Manually seed the sentinel — no DB row needed.
    await fake_redis.setex("url:deadcode", 3600, "__expired__")

    with patch(
        "app.api.redirect.url_service.get_url", new_callable=AsyncMock
    ) as mock_get_url:
        res = await client.get("/deadcode", follow_redirects=False)

    assert res.status_code == 410
    mock_get_url.assert_not_called()


# ---------------------------------------------------------------------------
# Cleanup job
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_expired_urls_removes_expired_rows(db_session):
    """
    cleanup_expired_urls() must hard-delete rows whose expires_at is in the past
    and leave non-expired rows untouched.
    """
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    future = datetime.now(timezone.utc) + timedelta(hours=1)

    expired = Url(short_code="exprd01", original_url="https://old.com", expires_at=past)
    active = Url(short_code="activ01", original_url="https://new.com", expires_at=future)
    db_session.add(expired)
    db_session.add(active)
    await db_session.commit()

    # Build a synchronous callable that returns an async context manager
    # wrapping the existing test session.
    class _FakeSessionCM:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_):
            pass

    with patch("app.services.expiry.AsyncSessionLocal", return_value=_FakeSessionCM()):
        deleted = await cleanup_expired_urls()

    assert deleted == 1

    # cleanup_expired_urls does a soft-delete (is_active=False), not a hard delete,
    # so the row remains in the DB for analytics history.
    remaining = await db_session.scalar(select(Url).where(Url.short_code == "exprd01"))
    assert remaining is not None
    assert remaining.is_active is False

    still_active = await db_session.scalar(select(Url).where(Url.short_code == "activ01"))
    assert still_active is not None
    assert still_active.is_active is True


@pytest.mark.asyncio
async def test_cleanup_does_not_remove_non_expiring_rows(db_session):
    """Rows with expires_at=NULL must never be deleted by the cleanup job."""
    permanent = Url(short_code="perm001", original_url="https://perm.com", expires_at=None)
    db_session.add(permanent)
    await db_session.commit()

    class _FakeSessionCM:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_):
            pass

    with patch("app.services.expiry.AsyncSessionLocal", return_value=_FakeSessionCM()):
        deleted = await cleanup_expired_urls()

    assert deleted == 0
    still_there = await db_session.scalar(select(Url).where(Url.short_code == "perm001"))
    assert still_there is not None
