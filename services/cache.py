"""Simple TTL-based in-memory cache implementation."""

import time
from typing import Any, Dict, Optional


class TTLCache:
    """A simple dictionary-based TTL cache."""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Retrieve a value from the cache if it exists and hasn't expired."""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                # Remove expired entry
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Store a value in the cache with a TTL (time-to-live) in seconds."""
        expiry = time.time() + ttl_seconds
        self._cache[key] = (value, expiry)
    
    def clear(self):
        """Clear all entries from the cache."""
        self._cache.clear()
        
    def cleanup_expired(self):
        """Remove expired entries from the cache."""
        now = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items() 
            if now >= expiry
        ]
        for key in expired_keys:
            del self._cache[key]


# Global cache instance
cache = TTLCache()