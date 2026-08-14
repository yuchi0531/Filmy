"""バックエンド結合テスト。

全 API エンドポイントを HTTP 経由で一気通貫に検証する（FastAPI → ルーター →
スクレイパー → パーサーの実コードを全て通す）。

- スクレイパー・ルーターはモックせず実コードで動作させる
- ネットワーク層だけを :class:`tests.fake_client.FakeFilmarksClient` に差し替え、
  実際の Filmarks へのアクセスを防ぐ（モッククライアント方式）
- 既存の ``tests/conftest.py`` の autouse フィクスチャ（テスト設定・キャッシュクリア）を再利用
"""

from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from unittest import mock

from app.main import app
from tests import mock_html
from tests.fake_client import FakeFilmarksClient

# 検索キーワード（日本語をエンコードしてパスを構築する）
SEARCH_Q = "ドラえもん"

# モックページ（パス → HTML/JSON）。FakeFilmarksClient が応答する。
DEFAULT_PAGES: dict[str, str] = {
    "/list/now": mock_html.LIST_PAGE_HTML,
    "/list/coming": mock_html.LIST_PAGE_HTML,
    "/list/upcoming": mock_html.LIST_PAGE_HTML,
    "/list/trend": mock_html.LIST_PAGE_HTML,
    "/movies/1001": mock_html.DETAIL_PAGE_HTML,
    "/search/movies?q=" + quote(SEARCH_Q): mock_html.SEARCH_PAGE_HTML,
    "/theaters/tokyo": mock_html.THEATER_PREF_HTML,
    "/theaters/tokyo/99": mock_html.THEATER_AREA_HTML,
    "/theaters/tokyo/99/172": mock_html.THEATER_DETAIL_HTML,
    "/pia_theaters?latitude=35.0&longitude=139.0&radius=10.0": mock_html.NEARBY_JSON,
}


@pytest.fixture
def client() -> TestClient:
    """全エンドポイント用のモックページを持つテストクライアント。

    ``run_scrape``（app.routers.common）が参照する ``FilmarksClient`` を
    FakeFilmarksClient に差し替える。実ネットワークへは一切アクセスしない。
    """
    fake = FakeFilmarksClient(DEFAULT_PAGES)
    with mock.patch("app.routers.common.FilmarksClient", return_value=fake):
        with TestClient(app) as c:
            c.fake = fake  # type: ignore[attr-defined]
            yield c


# --- 映画一覧（now / coming / upcoming / trend） ---


@pytest.mark.parametrize(
    "endpoint",
    ["now", "coming", "upcoming", "trend"],
)
def test_movie_list_endpoints_ok(client, endpoint):
    r = client.get(f"/api/movies/{endpoint}")
    assert r.status_code == 200
    data = r.json()
    assert data["heading"] == "上映中の最新映画 459作品"
    assert data["total"] == 459
    assert data["page"] == 1
    assert data["has_next"] is True
    assert len(data["results"]) == 2

    first = data["results"][0]
    assert first["id"] == "1001"
    assert first["title"] == "テスト映画A"
    assert first["rating"] == 3.5
    assert first["genres"] == ["ドラマ", "SF"]
    assert first["release_date"] == "2026年08月01日"

    second = data["results"][1]
    assert second["id"] == "1002"
    assert second["rating"] is None  # 評価の無いカード


def test_movie_list_cached_on_second_call(client):
    """2回目以降はキャッシュヒットし、スクレイパー（fake client）が呼ばれない。"""
    r1 = client.get("/api/movies/now")
    assert r1.status_code == 200

    r2 = client.get("/api/movies/now")
    assert r2.status_code == 200
    assert r1.json() == r2.json()

    # /list/now への実スクレイピングは1回だけ
    assert client.fake.calls.count("/list/now") == 1


def test_movie_list_paging_ok(client):
    """page=2 は別のパス（?page=2）を取得する（1回だけリクエストされる）。"""
    client.fake.pages["/list/now?page=2"] = mock_html.list_page_html(
        heading="上映中の最新映画 459作品（2ページ目）"
    )
    r = client.get("/api/movies/now", params={"page": 2})
    assert r.status_code == 200
    assert r.json()["page"] == 2
    assert client.fake.calls == ["/list/now?page=2"]


# --- 映画詳細 ---


def test_movie_detail_ok(client):
    r = client.get("/api/movies/1001")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "1001"
    assert data["title"] == "テスト映画A"
    assert data["original_title"] == "TEST MOVIE A"
    assert data["synopsis"] == "これはあらすじです。"
    assert data["rating"] == 3.5
    assert data["review_count"] == 42
    assert data["release_date"] == "2026年08月01日"
    assert data["runtime"] == "120分"
    assert data["genres"] == ["SF", "ドラマ"]
    assert data["director"] == ["山田監督"]
    assert data["official_site"] == "https://www.example.test/official"
    assert data["cast"][0]["name"] == "主演俳優"
    assert data["streaming"] == []


def test_movie_detail_not_found_returns_404(client):
    """存在しない映画ID → Filmarksの404ページ → HTTP 404。"""
    client.fake.pages["/movies/9999"] = mock_html.NOT_FOUND_PAGE_HTML
    r = client.get("/api/movies/9999")
    assert r.status_code == 404


# --- 検索 ---


def test_search_ok(client):
    r = client.get("/api/search", params={"q": SEARCH_Q})
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == SEARCH_Q
    assert data["heading"] == "テストに関する映画 3作品"
    assert data["total"] == 3
    assert data["has_next"] is False
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "2001"
    assert data["results"][0]["title"] == "検索結果映画"
    # エンコード済みパスが要求される
    assert client.fake.calls == ["/search/movies?q=" + quote(SEARCH_Q)]


# --- 劇場 ---


def test_theaters_prefecture_ok(client):
    r = client.get("/api/theaters/tokyo")
    assert r.status_code == 200
    data = r.json()
    assert data["prefecture"] == "東京都"
    assert data["total"] == 2
    areas = {a["id"]: a for a in data["results"]}
    assert areas["99"]["name"] == "新宿"
    assert areas["99"]["url"] == "/theaters/tokyo/99"
    assert areas["134"]["name"] == "有楽町"


def test_theaters_area_ok(client):
    r = client.get("/api/theaters/tokyo/99")
    assert r.status_code == 200
    data = r.json()
    assert data["prefecture"] == "東京都"
    assert data["total"] == 2
    theaters = {t["id"]: t for t in data["results"]}
    assert theaters["172"]["name"] == "テストシネマ新宿"
    assert theaters["172"]["area_id"] == "99"
    assert theaters["172"]["url"] == "/theaters/tokyo/99/172"


def test_theaters_detail_with_schedule_ok(client):
    r = client.get("/api/theaters/tokyo/99/172")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "172"
    assert data["name"] == "テストシネマ新宿"
    assert data["prefecture"] == "東京都"
    assert data["address"] == "東京都新宿区新宿3-1-1"
    assert data["map_url"] == "https://maps.google.com/?q=テストシネマ新宿"
    assert data["latitude"] is None
    assert data["longitude"] is None

    # スケジュール（JSON API）が合成される
    assert len(data["movies"]) == 1
    movie = data["movies"][0]
    assert movie["movie_id"] == "3001"
    assert movie["movie_title"] == "スケジュール映画"
    assert movie["poster_url"] == "https://img.example.test/sched.jpg"
    dates = movie["dates"]
    assert len(dates) == 3  # schedule_days=3
    for times in dates.values():
        assert times == ["10:00", "13:30"]


def test_theaters_nearby_ok(client):
    r = client.get(
        "/api/theaters/nearby",
        params={"lat": 35.0, "lng": 139.0, "radius": 10.0},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == 35.0
    assert data["longitude"] == 139.0
    assert data["radius_km"] == 10.0
    assert len(data["theaters"]) == 2
    first = data["theaters"][0]
    assert first["id"] == "172"
    assert first["name"] == "テストシネマ新宿"
    assert first["area_id"] == "99"
    assert first["url"] == "/theaters/tokyo/99/172"


def test_theaters_nearby_default_radius_ok(client):
    """radius 省略時はデフォルト10km。"""
    r = client.get("/api/theaters/nearby", params={"lat": 35.0, "lng": 139.0})
    assert r.status_code == 200
    assert r.json()["radius_km"] == 10.0


# --- エラーケース（404 / 503 / 422） ---


def test_unavailable_returns_503(client):
    """Filmarks 側が一時的にアクセス不可 → HTTP 503。"""
    client.fake.pages["/list/now"] = mock_html.UNAVAILABLE_PAGE_HTML
    r = client.get("/api/movies/now")
    assert r.status_code == 503


def test_movie_id_non_numeric_returns_422(client):
    r = client.get("/api/movies/abc")
    assert r.status_code == 422


def test_search_empty_q_returns_422(client):
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 422


def test_search_too_long_q_returns_422(client):
    r = client.get("/api/search", params={"q": "a" * 201})
    assert r.status_code == 422


def test_nearby_missing_params_returns_422(client):
    r = client.get("/api/theaters/nearby")
    assert r.status_code == 422


def test_nearby_invalid_radius_returns_422(client):
    r = client.get(
        "/api/theaters/nearby",
        params={"lat": 35.0, "lng": 139.0, "radius": 200},
    )
    assert r.status_code == 422


def test_non_numeric_movie_path_returns_422(client):
    """movie_id パスは数字のみ許可 → 数字以外は 422。"""
    r = client.get("/api/movies/unknown-path")
    assert r.status_code == 422


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
