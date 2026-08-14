"""app/geocode.py のテスト（実ネットワーク不使用）。

``httpx.MockTransport`` でトランスポートを差し替え、国土地理院APIの
GeoJSON レスポンス解析のみを検証する。
"""

import httpx

from app import geocode

# conftest.py の autouse フィクスチャが ``geocode.geocode_address`` を
# None を返すスタブに差し替えるため、import 時点の実関数を退避して使う。
_real_geocode_address = geocode.geocode_address


def _patch_client(monkeypatch, handler) -> None:
    """``httpx.Client`` を ``MockTransport`` 版に差し替える。

    ``geocode_address`` は内部で ``httpx.Client(...)`` を直接生成するため、
    ``httpx.Client`` を transport 注入済みのファクトリにモンキーパッチする。
    """
    transport = httpx.MockTransport(handler)
    original = httpx.Client

    def factory(**kwargs):
        return original(transport=transport, **kwargs)

    monkeypatch.setattr(geocode.httpx, "Client", factory)


def _feature(longitude: float, latitude: float) -> list[dict]:
    return [
        {
            "geometry": {"coordinates": [longitude, latitude], "type": "Point"},
            "type": "Feature",
            "properties": {"addressCode": "13101", "title": "住所"},
        }
    ]


def test_geocode_returns_lat_lng_order(monkeypatch):
    """GeoJSON の ``[経度, 緯度]`` が ``(緯度, 経度)`` に変換されること。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "msearch.gsi.go.jp"
        assert request.url.params["q"] == "東京都新宿区新宿3-1-1"
        return httpx.Response(
            200, json=_feature(139.7036, 35.6905), request=request
        )

    _patch_client(monkeypatch, handler)

    assert _real_geocode_address("東京都新宿区新宿3-1-1") == (35.6905, 139.7036)


def test_geocode_empty_result_returns_none(monkeypatch):
    """空の Feature 配列は None を返すこと。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[], request=request)

    _patch_client(monkeypatch, handler)

    assert _real_geocode_address("存在しない住所") is None


def test_geocode_http_error_returns_none(monkeypatch):
    """HTTP エラー（非200）は None を返すこと。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="error", request=request)

    _patch_client(monkeypatch, handler)

    assert _real_geocode_address("東京都新宿区新宿3-1-1") is None


def test_geocode_invalid_payload_returns_none(monkeypatch):
    """coordinates を持たない不正なレスポンスは None を返すこと。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json=[{"type": "Feature", "geometry": None}], request=request
        )

    _patch_client(monkeypatch, handler)

    assert _real_geocode_address("東京都新宿区新宿3-1-1") is None


def test_geocode_network_error_returns_none(monkeypatch):
    """接続エラー（タイムアウト等）は None を返すこと。"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connection timed out")

    _patch_client(monkeypatch, handler)

    assert _real_geocode_address("東京都新宿区新宿3-1-1") is None


def test_geocode_empty_address_returns_none():
    """空文字・空白のみの住所は None を返すこと（ネットワークアクセス無し）。"""
    assert _real_geocode_address("") is None
    assert _real_geocode_address("   ") is None
