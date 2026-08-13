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