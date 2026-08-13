"""ルーター共通のスクレイピング実行ヘルパー。"""

import logging

from fastapi import HTTPException

from app.scrapers.exceptions import (
    FilmarksError,
    FilmarksNotFoundError,
    FilmarksUnavailableError,
)
from app.scrapers.http_client import FilmarksClient

logger = logging.getLogger(__name__)


def run_scrape(fn):
    """FilmarksClient のリソースを管理しながらスクレイピングを実行し、
    スクレイピング例外を HTTP ステータスコードに変換する。

    - :class:`FilmarksNotFoundError` → 404
    - :class:`FilmarksUnavailableError` → 503
    - :class:`FilmarksError`（パース失敗等） → 500
    - その他の予期しない例外（ValueError 等）→ ログ出力して 500
      （生の例外がそのまま500として漏れるのを防ぐ汎用ハンドラ）
    """
    try:
        with FilmarksClient() as client:
            return fn(client)
    except FilmarksNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FilmarksUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except FilmarksError as exc:
        logger.error("Filmarks スクレイピングでエラーが発生しました: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("予期しないエラーが発生しました: %s", exc)
        raise HTTPException(status_code=500, detail="内部エラーが発生しました") from exc
