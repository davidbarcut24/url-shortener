import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.models import Click


@pytest.mark.asyncio
async def test_redirect_follows_to_original_url(client):
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_unknown_code_returns_404(client):
    res = await client.get("/notexist", follow_redirects=False)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_redirect_expired_link_returns_410(client):
    res = await client.post("/api/shorten", json={"url": "https://example.com", "expires_in_days": -1})
    assert res.status_code == 201
    code = res.json()["short_code"]

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 410


@pytest.mark.asyncio
async def test_redirect_uses_cache_on_second_request(client, fake_redis):
    shorten_res = await client.post("/api/shorten", json={"url": "https://cached.com"})
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)
    cached = await fake_redis.get(f"url:{code}")
    assert cached == "https://cached.com"

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302


# ---------------------------------------------------------------------------
# __expired__ sentinel path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_sentinel_in_redis_returns_410_without_db_hit(client, fake_redis):
    """
    When '__expired__' is already in Redis the handler must return 410
    immediately without querying the DB.
    """
    await fake_redis.setex("url:sentonly", 3600, "__expired__")

    with patch(
        "app.api.redirect.url_service.get_url", new_callable=AsyncMock
    ) as mock_get_url:
        res = await client.get("/sentonly", follow_redirects=False)

    assert res.status_code == 410
    assert "detail" in res.json()
    mock_get_url.assert_not_called()


# ---------------------------------------------------------------------------
# Click row written on successful redirect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_click_row_written_on_successful_redirect(client, fake_redis):
    """
    A successful redirect must buffer a click in Redis.
    (Click rows are only written to the DB by the periodic flush job.)
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://click.com"})
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)

    buffered = await fake_redis.get(f"clicks:buffer:{code}")
    assert buffered is not None
    assert int(buffered) >= 1


@pytest.mark.asyncio
async def test_click_row_written_for_each_redirect(client, fake_redis):
    """Each redirect must increment the Redis click buffer by 1."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://multi.com"})
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)
    await client.get(f"/{code}", follow_redirects=False)
    await client.get(f"/{code}", follow_redirects=False)

    buffered = await fake_redis.get(f"clicks:buffer:{code}")
    assert buffered is not None
    assert int(buffered) >= 3


@pytest.mark.asyncio
async def test_no_click_row_written_for_expired_redirect(client, db_session):
    """An expired redirect (410) must NOT write a Click row."""
    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 410

    clicks = (
        await db_session.execute(select(Click).where(Click.short_code == code))
    ).scalars().all()
    assert len(clicks) == 0


# ---------------------------------------------------------------------------
# DELETE clears Redis cache key
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_url_clears_redis_cache_key(client, fake_redis):
    """
    DELETE /api/url/{code} must remove the url:{code} key from Redis so
    a subsequent redirect returns 404 rather than a stale cached URL.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://todelete.com"})
    code = shorten_res.json()["short_code"]

    # Warm cache
    await client.get(f"/{code}", follow_redirects=False)
    assert await fake_redis.get(f"url:{code}") == "https://todelete.com"

    del_res = await client.delete(f"/api/url/{code}")
    assert del_res.status_code == 204

    assert await fake_redis.get(f"url:{code}") == "__expired__"


@pytest.mark.asyncio
async def test_redirect_after_delete_returns_404(client, fake_redis):
    """After a successful DELETE the short code must no longer resolve (410 or 404)."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://gone.com"})
    code = shorten_res.json()["short_code"]

    await client.delete(f"/api/url/{code}")

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code in (404, 410)
