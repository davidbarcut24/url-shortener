"""
Tests for Redis cache hit / miss behaviour in the redirect flow.

The redirect handler (app/api/redirect.py) implements:
  1. Cache miss  → DB hit → populate cache → redirect
  2. Cache hit   → redirect (no DB call)
  3. __expired__ sentinel in cache → 410 (no DB call)
  4. Cache TTL is bounded by the URL's remaining lifetime
  5. DELETE /api/url/{code} clears the cache key
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models import Url
from app.services.cache_service import _compute_ttl, cache_url
from app.config import settings


# ---------------------------------------------------------------------------
# Unit tests — cache_service helpers
# ---------------------------------------------------------------------------

def test_compute_ttl_no_expiry_returns_default():
    """A URL with no expiry must use the full DEFAULT_CACHE_TTL."""
    assert _compute_ttl(None) == settings.DEFAULT_CACHE_TTL


def test_compute_ttl_expiry_far_future_capped_at_default():
    """Remaining lifetime beyond DEFAULT_CACHE_TTL must be capped."""
    result = _compute_ttl(datetime.now(timezone.utc) + timedelta(days=365))
    assert result == settings.DEFAULT_CACHE_TTL


def test_compute_ttl_expiry_imminent_returns_short_ttl():
    """Remaining lifetime of ~10 s must produce a TTL close to 10."""
    result = _compute_ttl(datetime.now(timezone.utc) + timedelta(seconds=10))
    # Allow ±2 s for test execution time
    assert 8 <= result <= 12


def test_compute_ttl_already_expired_returns_minimum_of_1():
    """An already-expired URL's TTL must be at least 1 (never 0 or negative)."""
    result = _compute_ttl(datetime.now(timezone.utc) - timedelta(seconds=60))
    assert result >= 1


# ---------------------------------------------------------------------------
# Integration tests — cache miss path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_first_redirect_is_cache_miss_then_populates_cache(client, fake_redis):
    """
    First redirect: Redis key must not exist before the request and must be
    populated with the original URL after the redirect succeeds.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    before = await fake_redis.get(f"url:{code}")
    assert before is None

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302

    after = await fake_redis.get(f"url:{code}")
    assert after == "https://example.com"


@pytest.mark.asyncio
async def test_cache_miss_still_redirects_correctly(client, fake_redis):
    """On a cold cache miss the response must still be a valid 302 redirect."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://miss.com"})
    code = shorten_res.json()["short_code"]

    # Ensure cache is empty
    await fake_redis.delete(f"url:{code}")

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "https://miss.com"


# ---------------------------------------------------------------------------
# Integration tests — cache hit path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_second_redirect_is_served_from_cache_without_db_hit(client, fake_redis):
    """
    On the second redirect the cache is warm.  The DB must NOT be queried.
    We patch url_service.get_url and assert it is never called.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://hit.com"})
    code = shorten_res.json()["short_code"]

    # Warm the cache via the first redirect
    await client.get(f"/{code}", follow_redirects=False)
    assert await fake_redis.get(f"url:{code}") == "https://hit.com"

    with patch(
        "app.api.redirect.url_service.get_url", new_callable=AsyncMock
    ) as mock_get_url:
        res = await client.get(f"/{code}", follow_redirects=False)

    assert res.status_code == 302
    assert res.headers["location"] == "https://hit.com"
    mock_get_url.assert_not_called()


@pytest.mark.asyncio
async def test_cache_hit_returns_correct_location_header(client, fake_redis):
    """Cache hit must return the same location header as a cache miss."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://cached.com"})
    code = shorten_res.json()["short_code"]

    res_miss = await client.get(f"/{code}", follow_redirects=False)
    res_hit = await client.get(f"/{code}", follow_redirects=False)

    assert res_miss.headers["location"] == res_hit.headers["location"]


# ---------------------------------------------------------------------------
# __expired__ sentinel
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_sentinel_returns_410(client, fake_redis):
    """A '__expired__' sentinel stored in Redis must yield 410."""
    await fake_redis.setex("url:expcode", 3600, "__expired__")

    res = await client.get("/expcode", follow_redirects=False)
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_expired_sentinel_does_not_hit_db(client, fake_redis):
    """
    When the '__expired__' sentinel is present the DB must never be consulted.
    """
    await fake_redis.setex("url:exponly", 3600, "__expired__")

    with patch(
        "app.api.redirect.url_service.get_url", new_callable=AsyncMock
    ) as mock_get_url:
        res = await client.get("/exponly", follow_redirects=False)

    assert res.status_code == 410
    mock_get_url.assert_not_called()


@pytest.mark.asyncio
async def test_expired_sentinel_written_after_db_expiry_check(client, fake_redis):
    """
    When the DB confirms a URL is expired the handler must write the sentinel
    to Redis so future requests short-circuit to 410 without another DB round-trip.
    """
    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)

    sentinel = await fake_redis.get(f"url:{code}")
    assert sentinel == "__expired__"


@pytest.mark.asyncio
async def test_real_url_value_is_not_treated_as_sentinel(client, fake_redis):
    """
    A URL whose value is not literally '__expired__' must always redirect (302),
    never 410, even if it looks unusual.
    """
    await fake_redis.setex("url:oddcode", 3600, "https://valid.com")

    with patch(
        "app.api.redirect.url_service.get_url", new_callable=AsyncMock
    ):
        res = await client.get("/oddcode", follow_redirects=False)

    assert res.status_code == 302
    assert res.headers["location"] == "https://valid.com"


# ---------------------------------------------------------------------------
# DELETE clears cache key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_url_removes_cache_key(client, fake_redis):
    """
    DELETE /api/url/{code} must evict the Redis cache key so a subsequent
    redirect returns 404 instead of a stale cached value.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://todelete.com"})
    code = shorten_res.json()["short_code"]

    # Warm the cache
    await client.get(f"/{code}", follow_redirects=False)
    assert await fake_redis.get(f"url:{code}") is not None

    del_res = await client.delete(f"/api/url/{code}")
    assert del_res.status_code == 204

    remaining = await fake_redis.get(f"url:{code}")
    # DELETE writes an __expired__ sentinel so in-flight requests cannot
    # repopulate the key with a stale URL.
    assert remaining == "__expired__"


@pytest.mark.asyncio
async def test_delete_url_then_redirect_returns_404(client, fake_redis):
    """After deletion, redirecting to the old code must return 410 (sentinel) or 404."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://todelete.com"})
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)  # warm cache

    await client.delete(f"/api/url/{code}")

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code in (404, 410)


@pytest.mark.asyncio
async def test_delete_clears_sentinel_key_too(client, fake_redis):
    """
    DELETE overwrites any existing cache value (including __expired__) with a
    fresh __expired__ sentinel to ensure the key is not stale.
    """
    await fake_redis.setex("url:sentcode", 3600, "__expired__")

    # Create a real DB row so DELETE finds something to delete.
    shorten_res = await client.post(
        "/api/shorten",
        json={"url": "https://example.com", "custom_code": "sentcode"},
    )
    assert shorten_res.status_code == 201

    del_res = await client.delete("/api/url/sentcode")
    assert del_res.status_code == 204

    remaining = await fake_redis.get("url:sentcode")
    assert remaining == "__expired__"


# ---------------------------------------------------------------------------
# Cache TTL agreement with DB expires_at
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_ttl_bounded_by_url_expiry(fake_redis):
    """
    cache_url must set a TTL that does not exceed the URL's remaining lifetime
    when expires_at is imminent.
    """
    url = Url(short_code="ttltest", original_url="https://ttl.com",
              expires_at=datetime.now(timezone.utc) + timedelta(seconds=30))

    await cache_url(fake_redis, url)

    ttl = await fake_redis.ttl("url:ttltest")
    # The key must exist and have a TTL <= 30 s (plus small margin for clock skew)
    assert 0 < ttl <= 32


@pytest.mark.asyncio
async def test_cache_ttl_is_default_for_non_expiring_url(fake_redis):
    """
    For URLs with no expiry, the TTL must equal DEFAULT_CACHE_TTL.
    """
    url = Url(short_code="noexp01", original_url="https://noexpiry.com", expires_at=None)

    await cache_url(fake_redis, url)

    ttl = await fake_redis.ttl("url:noexp01")
    # Allow ±2 s to account for execution time between setex and ttl call
    assert abs(ttl - settings.DEFAULT_CACHE_TTL) <= 2
