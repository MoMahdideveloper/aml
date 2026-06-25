import os

from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=os.environ.get("RATELIMIT_STORAGE_URI", os.environ.get("REDIS_URL", "redis://localhost:6379/0")),
)


def init_extensions(app):
    """Initialize cross-cutting Flask extensions."""
    print(f"[DEBUG] Initializing extensions for app: {app}")
    redis_url = os.environ.get("REDIS_URL")

    app.config.setdefault("RATELIMIT_STORAGE_URI", os.environ.get("RATELIMIT_STORAGE_URI", redis_url))
    if redis_url:
        app.config.setdefault("CACHE_REDIS_URL", redis_url)

    cache_type = "SimpleCache"
    cache_default_timeout = int(os.environ.get("CACHE_DEFAULT_TIMEOUT_SECONDS", "300"))
    cache_redis_url = app.config.get("CACHE_REDIS_URL")
    if cache_redis_url and cache_redis_url.startswith("redis://"):
        cache_type = "RedisCache"

    app.config.setdefault("CACHE_TYPE", cache_type)
    app.config.setdefault("CACHE_DEFAULT_TIMEOUT", cache_default_timeout)
    if cache_type == "RedisCache":
        app.config.setdefault("CACHE_REDIS_URL", cache_redis_url)

    print(f"[DEBUG] Initializing cache with app: {app}")
    cache.init_app(app)
    print(f"[DEBUG] Cache initialized. Cache.app: {cache.app}")
    limiter.init_app(app)