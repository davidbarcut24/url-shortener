import hashlib
import hmac
from app.config import settings


def hash_ip(ip: str) -> str:
    return hmac.new(
        settings.IP_HASH_SALT.encode(), ip.encode(), hashlib.sha256
    ).hexdigest()
