import time
import threading
from typing import Any, Optional, Callable


class CacheService:
    """Thread-safe in-process TTL cache for settings, categories, banners, and featured items.
    
    IMPORTANT ARCHITECTURE RULES:
    1. Only cache read-heavy static/catalog data (categories, active banners, featured products, settings, combos).
    2. NEVER cache stock, cart, checkout, order, or payment data.
    3. Invalidate on every admin write.
    """

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        from flask import current_app
        try:
            if current_app and current_app.config.get("DEBUG", False):
                # In local debug mode, bypass cache so changes on cloud/local reflect instantly without delay
                return None
        except Exception:
            pass

        with self._lock:
            if key in self._cache:
                val, expires_at = self._cache[key]
                if expires_at is None or expires_at > time.time():
                    return val
                # Expired
                del self._cache[key]
        return None

    def set(self, key: str, val: Any, ttl: Optional[int] = 300):
        with self._lock:
            expires_at = time.time() + ttl if ttl is not None else None
            self._cache[key] = (val, expires_at)

    def delete(self, key: str):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()

    def invalidate_all(self):
        """Invalidate all cached items (called on admin writes)."""
        self.clear()

    def get_or_set(self, key: str, callback: Callable[[], Any], ttl: int = 300) -> Any:
        val = self.get(key)
        if val is not None:
            return val
        val = callback()
        self.set(key, val, ttl)
        return val


# Global cache instance
cache = CacheService()
