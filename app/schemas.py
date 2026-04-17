from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    url: str
    expires_in_days: int | None = None
    custom_code: str | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL must be 2048 characters or fewer")
        return v

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.isalnum() or len(v) > 10:
            raise ValueError("Custom code must be alphanumeric and max 10 characters")
        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    expires_at: datetime | None


class AnalyticsResponse(BaseModel):
    short_code: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: datetime | None
