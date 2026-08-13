"""インメモリキャッシュ基盤（cachetools）。

TTLCache はスレッドセーフなので、名前空間ごとに TTL 付きキャッシュを
持つシングルトンの CacheManager を提供する。
"""

import threading

from cachetools import TTLCache

# 名前空間ごとのキャッシュ最大エントリ数
CACHE_MAXSIZE = 256


class CacheManager:
    """名前空間ごとに TTL キャッシュを管理するクラス。

    - ``set(namespace, key, value, ttl)``: TTL付きで保存
    - ``get(namespace, key)``: 取得（無い場合は None）
    """

    def __init__(self, maxsize: int = CACHE_MAXSIZE) -> None:
        self._maxsize = maxsize
        self._caches: dict[str, TTLCache] = {}
        # 名前空間ごとに、そのキャッシュを生成した際の TTL を記録する
        self._ttls: dict[str, float] = {}
        self._lock = threading.Lock()

    def _cache_for(self, namespace: str, ttl: float) -> TTLCache:
        with self._lock:
            cache = self._caches.get(namespace)
            # L4: 既存キャッシュの TTL と異なる ttl が渡されたら作り直す。
            # これにより「最初の TTL で生成され、以降の TTL 引数が無視される」
            # 落とし穴を防ぐ。通常は名前空間ごとに TTL は一定なので作り直しは発生しない。
            if cache is None or self._ttls.get(namespace) != ttl:
                cache = TTLCache(maxsize=self._maxsize, ttl=ttl)
                self._caches[namespace] = cache
                self._ttls[namespace] = ttl
        return cache

    def get(self, namespace: str, key: str):
        cache = self._caches.get(namespace)
        if cache is None:
            return None
        return cache.get(key)

    def set(self, namespace: str, key: str, value, ttl: float) -> None:
        cache = self._cache_for(namespace, ttl)
        cache[key] = value


# アプリ全体で共有するシングルトンインスタンス
cache_manager = CacheManager()

__all__ = ["CacheManager", "cache_manager"]