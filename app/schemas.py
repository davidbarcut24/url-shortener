import ipaddress
import socket
from datetime import datetime
from urllib.parse import urlparse
from pydantic import BaseModel, field_validator


def _is_ssrf_risk(url: str) -> bool:
    """Return True if the URL resolves to a private, loopback, or link-local address."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return True
        # Resolve the hostname to an IP address.  Use getaddrinfo so we also
        # catch IPv6 loopback/link-local addresses.
        infos = socket.getaddrinfo(hostname, None)
        for info in infos:
            raw_ip = info[4][0]
            # Strip IPv6 zone IDs (e.g. "fe80::1%eth0") before parsing.
            raw_ip = raw_ip.split("%")[0]
            addr = ipaddress.ip_address(raw_ip)
            if (
                addr.is_loopback
                or addr.is_private
                or addr.is_link_local
                or addr.is_reserved
                or addr.is_unspecified
            ):
                return True
        return False
    except (socket.gaierror, ValueError):
        # Cannot resolve — treat as safe to avoid blocking valid URLs during
        # DNS outages; a malicious actor cannot easily force a DNS failure.
        return False


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
        if _is_ssrf_risk(v):
            raise ValueError("URL must not resolve to a private or reserved address")
        return v

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 1:
            raise ValueError("Custom code must be at least 1 character")
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
