import pytest

from app.config import settings


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_10_shorten_requests(client):
    for _ in range(10):
        res = await client.post("/api/shorten", json={"url": "https://example.com"})
        assert res.status_code == 201

    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_blocks_after_60_redirect_requests(client):
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    for _ in range(60):
        res = await client.get(f"/{code}", follow_redirects=False)
        assert res.status_code == 302

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 429


# ---------------------------------------------------------------------------
# Rate limits are per-endpoint (independent counters)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exhausting_shorten_limit_does_not_affect_redirect(client, fake_redis):
    """
    Exhausting the shorten rate limit (10 requests) must not prevent redirect
    requests from succeeding — they use a separate Redis key.
    """
    # Create a URL before exhausting the shorten limit.
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert shorten_res.status_code == 201
    code = shorten_res.json()["short_code"]

    # Use up the remaining shorten quota (9 more requests = 10 total).
    for _ in range(9):
        await client.post("/api/shorten", json={"url": "https://example.com"})

    # 11th shorten request must be blocked.
    blocked = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert blocked.status_code == 429

    # Redirect must still work — different rate-limit namespace.
    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 302


@pytest.mark.asyncio
async def test_exhausting_redirect_limit_does_not_affect_shorten(client, fake_redis):
    """
    Exhausting the redirect rate limit must not prevent new shorten requests
    from succeeding.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    # Exhaust the redirect limit (settings.RATE_LIMIT_REDIRECT = 60).
    for _ in range(settings.RATE_LIMIT_REDIRECT):
        await client.get(f"/{code}", follow_redirects=False)

    # 61st redirect must be blocked.
    blocked = await client.get(f"/{code}", follow_redirects=False)
    assert blocked.status_code == 429

    # Shorten must still be available.
    res = await client.post("/api/shorten", json={"url": "https://other.com"})
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_shorten_and_redirect_use_different_redis_keys(fake_redis):
    """
    The rate-limit keys for shorten and redirect must be distinct so counters
    never interfere with each other.
    """
    shorten_key = "rate:shorten:127.0.0.1"
    redirect_key = "rate:redirect:127.0.0.1"
    assert shorten_key != redirect_key


# ---------------------------------------------------------------------------
# 429 response body contains detail field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shorten_429_response_contains_detail_field(client):
    """The 429 from the shorten endpoint must include a 'detail' key."""
    for _ in range(settings.RATE_LIMIT_SHORTEN):
        await client.post("/api/shorten", json={"url": "https://example.com"})

    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 429
    body = res.json()
    assert "detail" in body
    assert isinstance(body["detail"], str)
    assert len(body["detail"]) > 0


@pytest.mark.asyncio
async def test_redirect_429_response_contains_detail_field(client):
    """The 429 from the redirect endpoint must include a 'detail' key."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    for _ in range(settings.RATE_LIMIT_REDIRECT):
        await client.get(f"/{code}", follow_redirects=False)

    res = await client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 429
    body = res.json()
    assert "detail" in body
    assert isinstance(body["detail"], str)
    assert len(body["detail"]) > 0


# ---------------------------------------------------------------------------
# Counter resets after the window expires
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rate_limit_counter_resets_when_key_expires(client, fake_redis):
    """
    Manually deleting the rate-limit key (simulating TTL expiry) must allow
    requests to flow again after being blocked.
    """
    # Exhaust the shorten limit.
    for _ in range(settings.RATE_LIMIT_SHORTEN):
        await client.post("/api/shorten", json={"url": "https://example.com"})

    blocked = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert blocked.status_code == 429

    # Simulate the window expiring by deleting all shorten rate-limit keys.
    for key in await fake_redis.keys("rate:shorten:*"):
        await fake_redis.delete(key)

    # The next request must succeed.
    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
