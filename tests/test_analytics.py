import pytest
from sqlalchemy import select, update

from app.models import Url


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


# ---------------------------------------------------------------------------
# Exact arithmetic: DB click_count + Redis buffer = reported total
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_total_is_db_plus_buffer(client, db_session, fake_redis):
    """
    When the DB row has click_count=3 and the Redis buffer holds 7, the
    analytics endpoint must report exactly 10.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    # Force the DB click_count to exactly 3.
    await db_session.execute(
        update(Url).where(Url.short_code == code).values(click_count=3)
    )
    await db_session.commit()

    # Set the Redis buffer to 7.
    await fake_redis.set(f"clicks:buffer:{code}", "7")

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    assert res.json()["click_count"] == 10


@pytest.mark.asyncio
async def test_analytics_total_with_zero_buffer(client, db_session, fake_redis):
    """When the Redis buffer is absent the total must equal the DB click_count."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    await db_session.execute(
        update(Url).where(Url.short_code == code).values(click_count=4)
    )
    await db_session.commit()

    # Ensure no buffer key exists
    await fake_redis.delete(f"clicks:buffer:{code}")

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    assert res.json()["click_count"] == 4


@pytest.mark.asyncio
async def test_analytics_total_with_zero_db_count(client, fake_redis):
    """When DB click_count=0 the total must equal the Redis buffer value."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    await fake_redis.set(f"clicks:buffer:{code}", "9")

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    assert res.json()["click_count"] == 9


# ---------------------------------------------------------------------------
# Analytics on an expired URL returns 200 (not 404)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_on_expired_url_returns_200(client):
    """
    get_analytics does not filter by expiry.  An expired URL's analytics
    data must still be accessible (HTTP 200) so operators can review traffic.
    """
    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    assert shorten_res.status_code == 201
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_analytics_on_expired_url_not_confused_with_missing(client):
    """
    The 200 on an expired URL must be distinct from the 404 on a code that
    was never created.
    """
    shorten_res = await client.post(
        "/api/shorten", json={"url": "https://example.com", "expires_in_days": -1}
    )
    code = shorten_res.json()["short_code"]

    expired_res = await client.get(f"/api/analytics/{code}")
    missing_res = await client.get("/api/analytics/neverexisted")

    assert expired_res.status_code == 200
    assert missing_res.status_code == 404


# ---------------------------------------------------------------------------
# Full response body shape
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_analytics_full_response_body_shape(client):
    """
    The analytics response must include exactly the fields defined in
    AnalyticsResponse: short_code, original_url, click_count, created_at,
    expires_at.
    """
    shorten_res = await client.post("/api/shorten", json={"url": "https://shape.com"})
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/api/analytics/{code}")
    assert res.status_code == 200
    data = res.json()

    for field in ("short_code", "original_url", "click_count", "created_at", "expires_at"):
        assert field in data, f"Missing field in analytics response: {field}"


@pytest.mark.asyncio
async def test_analytics_response_field_types(client):
    """Each field in the analytics response must be the correct type."""
    shorten_res = await client.post(
        "/api/shorten",
        json={"url": "https://types.com", "expires_in_days": 7},
    )
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/api/analytics/{code}")
    data = res.json()

    assert isinstance(data["short_code"], str)
    assert isinstance(data["original_url"], str)
    assert isinstance(data["click_count"], int)
    assert isinstance(data["created_at"], str)   # ISO-8601 string from JSON
    assert isinstance(data["expires_at"], str)   # ISO-8601 string from JSON


@pytest.mark.asyncio
async def test_analytics_short_code_matches_requested_code(client):
    """The short_code in the analytics response must match the one requested."""
    shorten_res = await client.post(
        "/api/shorten",
        json={"url": "https://example.com", "custom_code": "mycode2"},
    )
    res = await client.get("/api/analytics/mycode2")
    assert res.status_code == 200
    assert res.json()["short_code"] == "mycode2"


@pytest.mark.asyncio
async def test_analytics_original_url_matches_input(client):
    """The original_url field must exactly match the URL that was shortened."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://original.com"})
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/api/analytics/{code}")
    assert res.json()["original_url"] == "https://original.com"


@pytest.mark.asyncio
async def test_analytics_expires_at_null_for_non_expiring_url(client):
    """expires_at must be null in the analytics response for a non-expiring URL."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    res = await client.get(f"/api/analytics/{code}")
    assert res.json()["expires_at"] is None


@pytest.mark.asyncio
async def test_analytics_click_count_increments_on_redirect(client):
    """Each redirect must cause the reported click_count to increase by at least 1."""
    shorten_res = await client.post("/api/shorten", json={"url": "https://example.com"})
    code = shorten_res.json()["short_code"]

    res_before = await client.get(f"/api/analytics/{code}")
    count_before = res_before.json()["click_count"]

    await client.get(f"/{code}", follow_redirects=False)

    res_after = await client.get(f"/api/analytics/{code}")
    count_after = res_after.json()["click_count"]

    assert count_after > count_before
