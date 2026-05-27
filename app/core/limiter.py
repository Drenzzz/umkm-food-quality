import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_rate_limit_key(request) -> str:  # type: ignore[no-untyped-def]
    # Skip rate limiting entirely in test environment so TestClient requests
    # from the same synthetic IP do not exhaust per-minute buckets.
    if os.environ.get("APP_ENV") == "test":
        return ""
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key, default_limits=["100/minute"])
