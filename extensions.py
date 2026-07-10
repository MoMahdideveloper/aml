import os

from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


cache = Cache()
# Default to in-memory limits so local/tests work without Redis.
# Production multi-node: set RATELIMIT_STORAGE_URI=redis://...
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
)


def init_extensions(app):
    """Initialize cross-cutting Flask extensions."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    rate_storage = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    app.config.setdefault("RATELIMIT_STORAGE_URI", rate_storage)
    app.config.setdefault("CACHE_REDIS_URL", os.environ.get("CACHE_REDIS_URL", redis_url))

    # Prefer SimpleCache unless explicitly forced to Redis.
    use_redis_cache = os.environ.get("CACHE_USE_REDIS", "0") == "1"
    cache_type = "RedisCache" if use_redis_cache else "SimpleCache"
    cache_default_timeout = int(os.environ.get("CACHE_DEFAULT_TIMEOUT_SECONDS", "300"))
    cache_redis_url = app.config.get("CACHE_REDIS_URL")

    app.config.setdefault("CACHE_TYPE", cache_type)
    app.config.setdefault("CACHE_DEFAULT_TIMEOUT", cache_default_timeout)
    if cache_type == "RedisCache" and cache_redis_url:
        app.config.setdefault("CACHE_REDIS_URL", cache_redis_url)

    cache.init_app(app)
    limiter.init_app(app)
