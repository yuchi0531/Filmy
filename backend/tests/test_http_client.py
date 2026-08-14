"""app/scrapers/http_client.py のテスト（実ネットワーク不使用）。

``httpx.MockTransport`` でトランスポートを差し替え、実HTTPリクエストを
一切行わずに以下を検証する:

- 404 → FilmarksNotFoundError
- 401/403/429 → FilmarksUnavailableError（アクセス不可）
- 5xx（500/502/503/504）→ FilmarksUnavailableError（一時的なサーバー障害）
- 想定外（418 等）→ FilmarksError
- タイムアウト → FilmarksUnavailableError
- リクエスト間隔（スロットル）が守られること
"""

import time

import httpx
import pytest

from app.scrapers.exceptions import (
    FilmarksError,
    FilmarksNotFoundError,
    FilmarksUnavailableError,
)
from app.scrapers.http_client import FilmarksClient

_BASE = "https://filmarks.example.test"


def _client(handler) -> FilmarksClient:
    """MockTransport を使った FilmarksClient を返す（実ネットワーク不使用）。"""
    transport = httpx.MockTransport(handler)
    return FilmarksClient(base_url=_BASE, transport=transport)


def _status_handler(status: int):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text="error", request=request)

    return handler


# --- ステータスコード分類 ---


def test_ok_returns_text():
    def handler(request):
        return httpx.Response(200, text="<html>ok</html>", request=request)

    client = _client(handler)
    try:
        assert client.get_html("/list/now") == "<html>ok</html>"
    finally:
        client.close()


@pytest.mark.parametrize("status", [404])
def test_404_raises_not_found(status):
    client = _client(_status_handler(status))
    try:
        with pytest.raises(FilmarksNotFoundError):
            client.get_html("/movies/1")
    finally:
        client.close()


@pytest.mark.parametrize("status", [401, 403, 429])
def test_auth_and_rate_limit_map_to_unavailable(status):
    client = _client(_status_handler(status))
    try:
        with pytest.raises(FilmarksUnavailableError):
            client.get_html("/list/now")
    finally:
        client.close()


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_5xx_map_to_unavailable(status):
    client = _client(_status_handler(status))
    try:
        with pytest.raises(FilmarksUnavailableError):
            client.get_html("/list/now")
    finally:
        client.close()


def test_unexpected_status_maps_to_filmarks_error():
    client = _client(_status_handler(418))
    try:
        with pytest.raises(FilmarksError):
            client.get_html("/list/now")
    finally:
        client.close()


# --- タイムアウト ---


def test_timeout_maps_to_unavailable():
    def handler(request):
        raise httpx.ConnectTimeout("connection timed out")

    client = _client(handler)
    try:
        with pytest.raises(FilmarksUnavailableError):
            client.get_html("/movies/1")
    finally:
        client.close()


# --- スロットル（リクエスト間隔） ---


def test_throttle_interval_respected(monkeypatch):
    """連続リクエストが設定した間隔以上あけて実行されること。

    _throttle_interval はモジュール起動時（既定5秒）から固定で、コンストラクタでは
    変更しない。ここではテスト専用に monkeypatch で小さな間隔に差し替えて検証する。
    """
    calls: list[str] = []

    def handler(request):
        calls.append(str(request.url.path))
        return httpx.Response(200, text="ok", request=request)

    interval = 0.05
    # グローバル間隔をテスト内だけで差し替える（teardown で元の値に戻る）
    monkeypatch.setattr(
        "app.scrapers.http_client._throttle_interval", interval
    )
    client = _client(handler)
    try:
        start = time.monotonic()
        client.get_html("/a")
        client.get_html("/b")
        elapsed = time.monotonic() - start
    finally:
        client.close()

    # 2回目のリクエストが interval 以上待たされる
    assert calls == ["/a", "/b"]
    assert elapsed >= interval - 0.005