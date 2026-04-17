import pytest


@pytest.mark.asyncio
async def test_shorten_returns_short_url(client):
    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    data = res.json()
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"
    assert len(data["short_code"]) == 7


@pytest.mark.asyncio
async def test_shorten_rejects_non_http_url(client):
    res = await client.post("/api/shorten", json={"url": "javascript:alert(1)"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_shorten_rejects_url_over_2048_chars(client):
    long_url = "https://example.com/" + "a" * 2048
    res = await client.post("/api/shorten", json={"url": long_url})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_shorten_custom_code(client):
    res = await client.post("/api/shorten", json={"url": "https://example.com", "custom_code": "mycode"})
    assert res.status_code == 201
    assert res.json()["short_code"] == "mycode"


@pytest.mark.asyncio
async def test_shorten_duplicate_custom_code_returns_409(client):
    await client.post("/api/shorten", json={"url": "https://example.com", "custom_code": "taken"})
    res = await client.post("/api/shorten", json={"url": "https://other.com", "custom_code": "taken"})
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_shorten_invalid_custom_code_rejected(client):
    res = await client.post("/api/shorten", json={"url": "https://example.com", "custom_code": "bad code!"})
    assert res.status_code == 422
