import pytest


@pytest.mark.asyncio
async def test_analytics_returns_click_count(client, fake_redis):
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    await client.get(f"/{code}", follow_redirects=False)
    await client.get(f"/{code}", follow_redirects=False)

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    data = res.json()
    assert data["click_count"] >= 2


@pytest.mark.asyncio
async def test_analytics_includes_buffered_clicks(client, fake_redis):
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    await fake_redis.set(f"clicks:buffer:{code}", "5")

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    assert res.json()["click_count"] >= 5


@pytest.mark.asyncio
async def test_analytics_unknown_code_returns_404(client):
    res = await client.get("/api/analytics/doesnotexist")
    assert res.status_code == 404
