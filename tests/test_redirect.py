import pytest


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
