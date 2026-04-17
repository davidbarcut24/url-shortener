"""
Tests for short-code collision handling in the URL service.

The service has MAX_COLLISION_RETRIES = 5.  When every attempt produces a
code that is already taken it must raise CollisionError, which the API
translates to HTTP 409.  When only some attempts collide the service must
keep retrying until it finds a free slot, ensuring two different original
URLs always receive distinct short codes.
"""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.url_service import (
    create_short_url,
    CollisionError,
    MAX_COLLISION_RETRIES,
)
from app.models import Url


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_url_row(short_code: str) -> Url:
    """Return a minimal Url ORM instance for use as a mock return value."""
    return Url(
        short_code=short_code,
        original_url="https://taken.com",
        expires_at=None,
        click_count=0,
    )


# ---------------------------------------------------------------------------
# Unit tests — service layer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collision_retries_until_free_slot_found():
    """
    The first two generated codes collide with existing rows; the third is
    free.  The service must succeed on the third attempt and NOT raise.
    """
    db = AsyncMock(spec=AsyncSession)
    existing_row = _make_url_row("aaaaaaa")

    # scalar returns a taken row for the first two codes, then None (free).
    db.scalar.side_effect = [existing_row, existing_row, None]
    db.refresh = AsyncMock(return_value=None)

    with patch("app.services.url_service.generate_short_code", side_effect=["aaaaaaa", "bbbbbbb", "ccccccc"]):
        url = await create_short_url(db, "https://new.com")

    assert url.short_code == "ccccccc"
    # scalar must have been called exactly three times
    assert db.scalar.call_count == 3


@pytest.mark.asyncio
async def test_collision_raises_after_max_retries_exhausted():
    """
    When every generated code collides (MAX_COLLISION_RETRIES = 5), the
    service must raise CollisionError — never a bare exception or 500.
    """
    db = AsyncMock(spec=AsyncSession)
    existing_row = _make_url_row("aaaaaaa")
    # All 5 attempts return a taken row.
    db.scalar.side_effect = [existing_row] * MAX_COLLISION_RETRIES

    with patch(
        "app.services.url_service.generate_short_code",
        side_effect=["aaa0000", "aaa0001", "aaa0002", "aaa0003", "aaa0004"],
    ):
        with pytest.raises(CollisionError):
            await create_short_url(db, "https://always-collides.com")

    assert db.scalar.call_count == MAX_COLLISION_RETRIES


@pytest.mark.asyncio
async def test_collision_error_message_is_informative():
    """The CollisionError message must be a non-empty, human-readable string."""
    db = AsyncMock(spec=AsyncSession)
    existing_row = _make_url_row("aaaaaaa")
    db.scalar.side_effect = [existing_row] * MAX_COLLISION_RETRIES

    with patch("app.services.url_service.generate_short_code", return_value="aaaaaaa"):
        with pytest.raises(CollisionError) as exc_info:
            await create_short_url(db, "https://example.com")

    assert len(str(exc_info.value)) > 0


# ---------------------------------------------------------------------------
# Integration tests — HTTP layer
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_collision_after_max_retries_returns_409(client):
    """
    When the service cannot find a free code the API must return 409, not 500.
    """
    with patch(
        "app.services.url_service._generate_unique_code",
        side_effect=CollisionError("Failed to generate unique short code after maximum retries"),
    ):
        res = await client.post("/api/shorten", json={"url": "https://example.com"})

    assert res.status_code == 409
    body = res.json()
    assert "detail" in body
    assert len(body["detail"]) > 0


@pytest.mark.asyncio
async def test_two_urls_always_get_distinct_short_codes(client):
    """
    Two different original URLs shortened in the same session must receive
    different short codes.
    """
    res1 = await client.post("/api/shorten", json={"url": "https://first.com"})
    res2 = await client.post("/api/shorten", json={"url": "https://second.com"})

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["short_code"] != res2.json()["short_code"]


@pytest.mark.asyncio
async def test_custom_code_collision_returns_409_with_detail(client):
    """
    Requesting the same custom code twice must return 409 with a detail field
    explaining the conflict — not a generic server error.
    """
    await client.post(
        "/api/shorten", json={"url": "https://first.com", "custom_code": "abc123"}
    )
    res = await client.post(
        "/api/shorten", json={"url": "https://second.com", "custom_code": "abc123"}
    )

    assert res.status_code == 409
    body = res.json()
    assert "detail" in body
    assert "abc123" in body["detail"]


@pytest.mark.asyncio
async def test_same_url_shortened_twice_gets_distinct_codes(client):
    """
    Shortening the exact same URL a second time must produce a second, distinct
    short code (the service uses time_ns entropy, so codes differ).
    """
    res1 = await client.post("/api/shorten", json={"url": "https://same.com"})
    res2 = await client.post("/api/shorten", json={"url": "https://same.com"})

    assert res1.status_code == 201
    assert res2.status_code == 201
    # Codes should differ because time_ns changes between calls.
    assert res1.json()["short_code"] != res2.json()["short_code"]
