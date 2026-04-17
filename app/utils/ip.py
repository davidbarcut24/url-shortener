import hashlib
import hmac
from app.config import settings

_SALT = "url-shortener-ip-salt"


def hash_ip(ip: str) -> str:
    return hmac.new(_SALT.encode(), ip.encode(), hashlib.sha256).hexdigest()
