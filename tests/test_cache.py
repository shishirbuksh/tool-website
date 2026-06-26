import time

from app.core.cache import MemoryCache


class TestMemoryCache:
    def test_set_and_get(self):
        c = MemoryCache()
        c.set("key1", "value1")
        assert c.get("key1") == "value1"

    def test_get_expired(self):
        c = MemoryCache()
        c._default_ttl = 0
        c.set("key", "val")
        time.sleep(0.01)
        assert c.get("key") is None

    def test_get_missing(self):
        c = MemoryCache()
        assert c.get("nonexistent") is None

    def test_delete(self):
        c = MemoryCache()
        c.set("key", "val")
        c.delete("key")
        assert c.get("key") is None

    def test_clear(self):
        c = MemoryCache()
        c.set("a", 1)
        c.set("b", 2)
        c.clear()
        assert c.get("a") is None
        assert c.get("b") is None

    def test_evict_when_full(self):
        c = MemoryCache()
        c._default_ttl = -1
        for i in range(1005):
            c.set(f"k{i}", i)
        assert len(c._data) <= 1000


class TestCacheService:
    def test_fallback_to_memory(self):
        from app.core.cache import CacheService
        svc = CacheService(default_ttl=60)
        svc.set("test_key", "hello")
        assert svc.get("test_key") == "hello"

    def test_delete(self):
        from app.core.cache import CacheService
        svc = CacheService()
        svc.set("del_key", "value")
        svc.delete("del_key")
        assert svc.get("del_key") is None

    def test_clear(self):
        from app.core.cache import CacheService
        svc = CacheService()
        svc.set("a", 1)
        svc.set("b", 2)
        svc.clear()
        assert svc.get("a") is None
        assert svc.get("b") is None
