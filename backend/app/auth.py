"""クライアント認証（X-API-Key ヘッダー）。"""

import hmac

from fastapi import Header, HTTPException

from app.config import settings


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """X-API-Key ヘッダーを検証する FastAPI dependency。

    - production かつ settings.api_key が空文字なら 503 を返す（fail-closed）。
      設定漏れで認証なしに全エンドポイントが公開されるのを防ぐ。
    - development では空文字なら認証をスキップ（ローカル開発・既存テスト互換）。
    - タイミング攻撃対策のため hmac.compare_digest で比較する。
    - 不一致/欠落は 401 を返す。
    """
    if not settings.api_key:
        if settings.environment == "production":
            raise HTTPException(
                status_code=503,
                detail="API key not configured (set FILMY_API_KEY)",
            )
        return
    if x_api_key is None or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="invalid or missing API key")
