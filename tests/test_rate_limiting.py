import pytest


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
