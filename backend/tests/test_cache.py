"""app/cache/__init__.py のテスト。"""

import asyncio
import threading
import time

import pytest

from app.cache import CacheManager


def test_set_and_get_normal():
    cache = CacheManager()
    cache.set("ns", "key", "value", ttl=60)
    assert cache.get("ns", "key") == "value"


def test_get_missing_namespace_returns_none():
    cache = CacheManager()
    assert cache.get("unknown", "key") is None


def test_get_missing_key_returns_none():
    cache = CacheManager()
    cache.set("ns", "a", "x", ttl=60)
    assert cache.get("ns", "b") is None


def test_overwrite_value():
    cache = CacheManager()
    cache.set("ns", "k", "old", ttl=60)
    cache.set("ns", "k", "new", ttl=60)
    assert cache.get("ns", "k") == "new"


def test_ttl_expiry_auto_removes():
    """短いTTLを設定し、経過後は get が None を返す。"""
    cache = CacheManager()
    cache.set("ns", "k", "v", ttl=0.05)
    assert cache.get("ns", "k") == "v"
    time.sleep(0.1)
    assert cache.get("ns", "k") is None


def test_namespace_isolation():
    """異なる名前空間では同じキーでも独立に管理される。"""
    cache = CacheManager()
    cache.set("ns1", "k", "one", ttl=60)
    cache.set("ns2", "k", "two", ttl=60)
    assert cache.get("ns1", "k") == "one"
    assert cache.get("ns2", "k") == "two"


def test_namespace_different_ttl_keeps_values():
    """名前空間ごとに異なるTTLで保持できる。"""
    cache = CacheManager()
    cache.set("a", "k", "short", ttl=0.05)
    cache.set("b", "k", "long", ttl=60)
    time.sleep(0.1)
    assert cache.get("a", "k") is None
    assert cache.get("b", "k") == "long"


def test_same_namespace_ttl_change_rebuilds_cache():
    """同じ名前空間でTTLが変わるとキャッシュを作り直す（古い値は失われる）。"""
    cache = CacheManager()
    cache.set("ns", "old", "v", ttl=60)
    cache.set("ns", "new", "v", ttl=30)  # TTL 違いで作り直し → old は消える
    assert cache.get("ns", "old") is None
    assert cache.get("ns", "new") == "v"


def test_thread_safety():
    """多数スレッドから並行 set/get しても破損しない。"""
    cache = CacheManager()
    errors: list[Exception] = []
    n = 50

    def worker(i: int) -> None:
        try:
            ns = f"ns{i % 5}"
            key = f"k{i}"
            cache.set(ns, key, i, ttl=60)
            got = cache.get(ns, key)
            if got != i:
                errors.append(AssertionError(f"ns={ns} expected {i} got {got}"))
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"並行アクセスでエラー発生: {errors}"


@pytest.mark.asyncio
async def test_thread_safety_async_context():
    """async コンテキスト（asyncio タスク）から並行アクセスしても安全。"""
    cache = CacheManager()
    results: dict[str, int] = {}

    async def worker(i: int) -> None:
        ns = "async"
        cache.set(ns, f"k{i}", i, ttl=60)
        results[f"k{i}"] = cache.get(ns, f"k{i}")

    await asyncio.gather(*(worker(i) for i in range(20)))
    for i in range(20):
        assert results[f"k{i}"] == i