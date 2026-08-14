"""pytest 共通フィクスチャ。

- ``app.config.Settings`` の設定値に モンキーパッチ を当てて、
  実ネットワークアクセスをさせない（実HTTPは使わない）。
- 共有 ``cache_manager`` をテスト間でクリアする。
- モックHTML/JSON を BeautifulSoup 化するヘルパーを提供する。
"""

from bs4 import BeautifulSoup
import pytest

from app.config import settings
from tests import mock_html
from tests.fake_client import FakeFilmarksClient


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch) -> None:
    """テスト用に設定を差し替える。

    FastAPI の各ルーターは ``app.config.settings`` の **同一インスタンス** を
    モジュールロード時に ``from app.config import settings`` で参照しているため、
    このインスタンスの属性を上書きする == Settings を差し替える ことと同じ効果になる。

    ネットワーク破壊防止のため、ベースURLを到達不能な .test ドメインにし、
    リクエスト間隔（スロットル）を 0 にしてテスト実行を高速化する。
    """
    monkeypatch.setattr(settings, "filmarks_base_url", "https://filmarks.example.test")
    monkeypatch.setattr(settings, "request_timeout", 1.0)
    monkeypatch.setattr(settings, "request_interval", 0.0)
    # プロセス共有スロットル（モジュールレベルのグローバル）も待機させない
    import app.scrapers.http_client as http_client

    monkeypatch.setattr(http_client, "_throttle_interval", 0.0)


@pytest.fixture(autouse=True)
def _clear_cache():
    """共有 cache_manager をテスト間でクリアしてキャッシュ漏れを防ぐ。"""
    from app.cache import cache_manager

    cache_manager.clear()
    yield


@pytest.fixture(autouse=True)
def _relax_rate_limit(monkeypatch):
    """テスト向けにレート制限を緩和し、グローバル状態をリセットする。

    - ``rate_limit_per_minute`` を十分大きな値に差し替え、結合テスト等で
      多数の HTTP リクエストが 429 にならないようにする。
    - レートリミッターの IP 別アクセス履歴（モジュールレベルのグローバル辞書）を
      テスト間でクリアし、状態が漏れないようにする。
    """
    monkeypatch.setattr(settings, "rate_limit_per_minute", 10000)

    import app.rate_limit as rate_limit

    with rate_limit._lock:
        rate_limit._requests.clear()
    yield


@pytest.fixture(autouse=True)
def _isolate_coord_cache_and_geocode(tmp_path, monkeypatch) -> None:
    """座標キャッシュ（SQLite）とジオコーディングをテスト用に分離する。

    - ``app.routers.theaters.coord_cache`` を一時ディレクトリの SQLite に差し替え、
      テスト実行時にリポジトリ内へ ``./data/theater_coords.db`` が生成されるのを防ぐ。
    - ``app.geocode.geocode_address`` を None を返すスタブに差し替え、
      テストが実ネットワーク（国土地理院API）へアクセスするのを防ぐ。

    テスト個別に座標を検証したい場合は、テスト内で monkeypatch により
    ``geocode_address`` を上書きできる（autouse フィクスチャより後に適用される）。
    """
    from app.coord_cache import CoordCache

    import app.routers.theaters as theaters_mod

    monkeypatch.setattr(
        theaters_mod,
        "coord_cache",
        CoordCache(str(tmp_path / "theater_coords.db")),
    )
    monkeypatch.setattr("app.geocode.geocode_address", lambda address: None)
    # 座標補完の in-flight 集合（モジュールレベルのグローバル）をテスト間でクリアし、
    # デーモンスレッドの finally クリーンアップと競合しても状態が漏れないようにする。
    with theaters_mod._in_flight_lock:
        theaters_mod._in_flight.clear()


@pytest.fixture
def make_soup():
    """HTML文字列を BeautifulSoup（lxml）に変換するヘルパーを返す。"""

    def _make(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    return _make


@pytest.fixture
def mock_pages() -> dict[str, str]:
    """スクレイパー単体テスト用のデフォルト モックページ群。"""
    return {
        "/list/now": mock_html.LIST_PAGE_HTML,
        "/theaters/tokyo": mock_html.THEATER_PREF_HTML,
        "/theaters/tokyo/99": mock_html.THEATER_AREA_HTML,
        "/theaters/tokyo/99/172": mock_html.THEATER_DETAIL_HTML,
        "/pia_theaters?latitude=35.0&longitude=139.0&radius=10.0": (
            mock_html.NEARBY_JSON
        ),
    }


@pytest.fixture
def fake_client(mock_pages: dict[str, str]) -> FakeFilmarksClient:
    """モックページ群を持ったフェイククライアントを返す。"""
    return FakeFilmarksClient(mock_pages)