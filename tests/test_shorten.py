import pytest

from app.config import settings


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


# ---------------------------------------------------------------------------
# Input validation edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shorten_empty_body_returns_422(client):
    """A completely empty JSON body must be rejected with 422."""
    res = await client.post("/api/shorten", json={})
    assert res.status_code == 422
    body = res.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_shorten_empty_string_url_returns_422(client):
    """An empty string URL must fail validation with 422."""
    res = await client.post("/api/shorten", json={"url": ""})
    assert res.status_code == 422
    body = res.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_shorten_url_exactly_2048_chars_is_accepted(client):
    """
    A URL that is exactly 2048 characters long must be accepted (the limit is
    inclusive: len(v) > 2048 is rejected, len(v) == 2048 passes).
    """
    # "https://x.com/" is 15 chars; pad with 'a' to reach exactly 2048.
    base = "https://x.com/"
    url_2048 = base + "a" * (2048 - len(base))
    assert len(url_2048) == 2048

    res = await client.post("/api/shorten", json={"url": url_2048})
    assert res.status_code == 201


@pytest.mark.asyncio
async def test_shorten_url_2049_chars_is_rejected(client):
    """A URL of 2049 characters must be rejected with 422."""
    base = "https://x.com/"
    url_2049 = base + "a" * (2049 - len(base))
    assert len(url_2049) == 2049

    res = await client.post("/api/shorten", json={"url": url_2049})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_shorten_custom_code_with_slash_returns_422(client):
    """A custom code containing '/' must be rejected with 422."""
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "custom_code": "ab/cd"}
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_shorten_custom_code_with_space_returns_422(client):
    """A custom code containing a space must be rejected with 422."""
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "custom_code": "ab cd"}
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_shorten_custom_code_over_10_chars_returns_422(client):
    """A custom code longer than 10 characters must be rejected with 422."""
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "custom_code": "a" * 11}
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_shorten_malformed_url_returns_422_with_detail(client):
    """A non-URL string must return 422 with a descriptive detail field."""
    res = await client.post("/api/shorten", json={"url": "not-a-url-at-all"})
    assert res.status_code == 422
    body = res.json()
    assert "detail" in body


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shorten_expires_at_null_when_no_expiry(client):
    """expires_at must be null in the response when no expires_in_days is given."""
    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    assert res.json()["expires_at"] is None


@pytest.mark.asyncio
async def test_shorten_expires_at_set_when_expires_in_days_given(client):
    """expires_at must be a non-null ISO-8601 string when expires_in_days is given."""
    res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": 5}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["expires_at"] is not None
    # Must be parseable as an ISO datetime
    from datetime import datetime
    parsed = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    assert parsed is not None


@pytest.mark.asyncio
async def test_shorten_short_url_format_matches_base_url(client):
    """
    The short_url field must be BASE_URL/{short_code} — i.e. the value from
    settings.BASE_URL followed by a slash and the short_code.
    """
    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    data = res.json()
    expected = f"{settings.BASE_URL}/{data['short_code']}"
    assert data["short_url"] == expected


@pytest.mark.asyncio
async def test_shorten_response_contains_all_required_fields(client):
    """The 201 response body must contain short_code, short_url, original_url, expires_at."""
    res = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert res.status_code == 201
    data = res.json()
    for field in ("short_code", "short_url", "original_url", "expires_at"):
        assert field in data, f"Missing field: {field}"
