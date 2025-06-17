from datetime import datetime, timedelta
from typing import Dict, Any
import threading
from functools import lru_cache

class CacheManager:
    def __init__(self):
        self._cache = {}
        self._cache_lock = threading.Lock()
        
    def get(self, key: str, ttl_seconds: int = 60) -> Any:
        """Get value from cache if not expired"""
        with self._cache_lock:
            if key in self._cache:
                value, timestamp = self._cache[key]
                if datetime.now() - timestamp < timedelta(seconds=ttl_seconds):
                    return value
                else:
                    del self._cache[key]
            return None
            
    def set(self, key: str, value: Any):
        """Set value in cache with current timestamp"""
        with self._cache_lock:
            self._cache[key] = (value, datetime.now())
            
    def clear(self):
        """Clear all cached values"""
        with self._cache_lock:
            self._cache.clear()

# Singleton instance
cache = CacheManager()
