"""クライアント向けレート制限（インメモリ・スレッドセーフ・IPごと）。"""

import threading
import time

from fastapi import HTTPException, Request

from app.config import settings

# IPごとのアクセス時刻リスト（モジュールレベルのグローバル状態）。
# キーはクライアントIP、値は直近60秒間のアクセス時刻（time.monotonic()）。
# 60秒より古い記録を捨ててリストが空になったらキーごと削除し、メモリ肥大化を防ぐ。
_requests: dict[str, list[float]] = {}
_lock = threading.Lock()


def _trusted_proxies() -> set[str]:
    """信頼できるリバースプロキシのIP集合（カンマ区切り設定をパース）。"""
    return {ip.strip() for ip in settings.trusted_proxies.split(",") if ip.strip()}


def _client_ip(request: Request) -> str | None:
    """リクエスト元のクライアントIPを返す。

    X-Forwarded-For は無条件には信頼しない。リクエスト元（request.client.host）
    が trusted_proxies に含まれる場合のみ XFF を採用する。

    - 直結（信頼プロキシ未経由）: request.client.host をそのまま使う。
      クライアントが任意に付与できる XFF をそのまま信じると、値を変えるだけで
      レート制限をバイパスできてしまうため、直結時は必ず無視する。
    - 信頼プロキシ経由: XFF は ``client, proxy1, proxy2`` の形式で、
      左端が元クライアント、以降が経由プロキシ。右端から走査して信頼プロキシを
      スキップし、最初に現れた非信頼IPをクライアントとみなす。
      （信頼プロキシが1つなら、これは「右から2番目＝クライアント」に一致する。）
    """
    if request.client is None:
        return None

    direct_ip = request.client.host
    trusted = _trusted_proxies()
    if not trusted or direct_ip not in trusted:
        return direct_ip

    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded:
        return direct_ip

    parts = [p.strip() for p in forwarded.split(",") if p.strip()]
    if not parts:
        return direct_ip

    # 右端（直近のプロキシ）から順に信頼プロキシをスキップし、
    # 最初の非信頼IPを元クライアントとして採用する。
    for part in reversed(parts):
        if part not in trusted:
            return part
    # 全要素が信頼プロキシの場合は末尾をフォールバックで返す
    return parts[-1]


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
        # 全IPの古い記録を破棄し、リストが空になったキーは削除する。
        # これにより、以後アクセスのないIPのキーが辞書に残り続けて
        # メモリが単調増加する（無制限肥大化）ことを防ぐ。
        for key in list(_requests.keys()):
            records = _requests[key]
            # 記録は単調増加で追加されるため、先頭から古いものを捨てる
            while records and records[0] < cutoff:
                records.pop(0)
            if not records:
                del _requests[key]

        records = _requests.get(ip)
        if records is None:
            records = []
            _requests[ip] = records
        if len(records) >= limit:
            raise HTTPException(status_code=429, detail="too many requests")
        records.append(now)
