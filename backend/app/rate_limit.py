"""クライアント向けレート制限（インメモリ・スレッドセーフ・IPごと）。"""

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import settings

# IPごとのアクセス時刻リスト（モジュールレベルのグローバル状態）。
# キーはクライアントIP、値は直近60秒間のアクセス時刻（time.monotonic()）。
_requests: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


def _client_ip(request: Request) -> str | None:
    """リクエスト元のIPを返す。

    プロキシ（Koyeb 等のリバースプロキシ）経由では request.client.host が
    プロキシのIPになるため、X-Forwarded-For があればその先頭IPを優先する。
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client is None:
        return None
    return request.client.host


def rate_limit(request: Request) -> None:
    """IPごとの簡易レートリミッター（FastAPI dependency）。

    - 直近60秒間のリクエスト数を IP ごとにカウントし、
      settings.rate_limit_per_minute を超えたら 429 を返す。
    - レート上限が 0 以下の場合は制限を無効化する（明示的な無効化手段）。
    """
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return

    ip = _client_ip(request)
    if ip is None:
        return

    now = time.monotonic()
    cutoff = now - 60.0

    with _lock:
        records = _requests[ip]
        # 60秒より古い記録を破棄（記録は単調増加で追加されるため先頭から捨てる）
        while records and records[0] < cutoff:
            records.pop(0)
        if len(records) >= limit:
            raise HTTPException(status_code=429, detail="too many requests")
        records.append(now)
