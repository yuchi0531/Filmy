"""FastAPI ルーターのAPIテスト。

``fastapi.testclient.TestClient`` で HTTP 経由のルーター挙動を検証する。
実ネットワークには一切アクセスせず、ルーターが参照するスクレイパークラスを
``mock.patch`` で差し替え、戻り値（Pydantic モデル）や例外を注入する。
"""

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.movie import MovieDetail, MovieListResponse, MovieSummary
from app.models.theater import AreaListResponse, AreaSummary
from app.scrapers.exceptions import (
    FilmarksNotFoundError,
    FilmarksParseError,
    FilmarksUnavailableError,
)
from tests import mock_html


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _movie_list_response() -> MovieListResponse:
    return MovieListResponse(
        query=None,
        heading="上映中の最新映画 459作品",
        results=[
            MovieSummary(
                id="1001",
                title="テスト映画A",
                rating=3.5,
                review_count=42,
                poster_url="https://img.example.test/a.jpg",
            )
        ],
        total=1,
        page=1,
        has_next=False,
    )


def _movie_detail() -> MovieDetail:
    return MovieDetail(
        id="1001",
        title="テスト映画A",
        original_title="TEST MOVIE A",
        synopsis="これはあらすじです。",
        rating=3.5,
        review_count=42,
    )


# --- 正常系 ---


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_movies_now_returns_list(client):
    with mock.patch("app.routers.movies.MovieListScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.parse.return_value = _movie_list_response()

        r = client.get("/api/movies/now")

    assert r.status_code == 200
    data = r.json()
    assert data["heading"] == "上映中の最新映画 459作品"
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["results"][0]["id"] == "1001"
    assert data["results"][0]["title"] == "テスト映画A"


def test_movie_detail_returns_detail(client):
    with mock.patch("app.routers.movies.MovieDetailScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.parse.return_value = _movie_detail()

        r = client.get("/api/movies/1001")

    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "1001"
    assert data["title"] == "テスト映画A"
    assert data["original_title"] == "TEST MOVIE A"
    assert data["synopsis"] == "これはあらすじです。"


def test_search_returns_list(client):
    with mock.patch("app.routers.search.MovieSearchScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.parse.return_value = _movie_list_response()

        r = client.get("/api/search", params={"q": "test"})

    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1


def test_theaters_tokyo_returns_area_list(client):
    with mock.patch("app.routers.theaters.TheaterListScraper") as MockScraper:
        instance = MockScraper.return_value
        # _prefecture_list は fetch_prefecture(prefecture) を使う
        instance.fetch_prefecture.return_value = (
            "東京都",
            [("99", "新宿"), ("134", "有楽町")],
        )

        r = client.get("/api/theaters/tokyo")

    assert r.status_code == 200
    data = r.json()
    assert data["prefecture"] == "東京都"
    assert data["total"] == 2
    assert [a["id"] for a in data["results"]] == ["99", "134"]
    assert data["results"][0]["name"] == "新宿"
    assert data["results"][0]["url"] == "/theaters/tokyo/99"


def test_theaters_nearby_returns_list(client):
    """/api/theaters/nearby が近隣劇場JSONをパースして返すこと。

    _nearby は run_scrape 内で FilmarksClient を作るため、client.get_html を
    mock で NEARBY_JSON（/pia_theaters レスポンス）に差し替えて検証する。
    run_scrape が参照するのは app.routers.common.FilmarksClient である点に注意。
    """
    with mock.patch("app.routers.common.FilmarksClient") as MockClient:
        instance = MockClient.return_value
        instance.__enter__.return_value = instance
        instance.get_html.return_value = mock_html.NEARBY_JSON
        # 座標補完の詳細ページ取得は失敗（None）として扱う
        instance.get_html_batch.return_value = [None, None]

        r = client.get(
            "/api/theaters/nearby",
            params={"lat": 35.0, "lng": 139.0, "radius": 10.0},
        )

    assert r.status_code == 200
    data = r.json()
    assert data["latitude"] == 35.0
    assert data["longitude"] == 139.0
    assert data["radius_km"] == 10.0
    theaters = data["theaters"]
    assert len(theaters) == 2
    # 1件目: /theaters/tokyo/99/172 → area_id "99"
    assert theaters[0]["id"] == "172"
    assert theaters[0]["name"] == "テストシネマ新宿"
    assert theaters[0]["area_id"] == "99"
    assert theaters[0]["url"] == "/theaters/tokyo/99/172"
    # 座標は取得できず None のまま
    assert theaters[0]["latitude"] is None
    assert theaters[0]["longitude"] is None
    # 2件目: /theaters/tokyo/88/200 → area_id "88"
    assert theaters[1]["id"] == "200"
    assert theaters[1]["area_id"] == "88"
    assert theaters[1]["url"] == "/theaters/tokyo/88/200"


def test_theaters_nearby_resolves_coords(client):
    """近隣検索で劇場の座標（緯度・経度）が補完され、SQLiteキャッシュに永続化されること。

    geocode_address をモックして座標を返し、詳細ページの住所から座標が解決される
    ことを検証する（実ネットワーク不使用）。
    """
    import app.routers.theaters as theaters_mod

    with mock.patch("app.routers.common.FilmarksClient") as MockClient:
        instance = MockClient.return_value
        instance.__enter__.return_value = instance
        instance.get_html.return_value = mock_html.NEARBY_JSON
        # 1件目は詳細ページ取得成功、2件目は失敗（None）
        instance.get_html_batch.return_value = [
            mock_html.THEATER_DETAIL_HTML,
            None,
        ]

        with mock.patch(
            "app.geocode.geocode_address", return_value=(35.68, 139.69)
        ) as geoc:
            r = client.get(
                "/api/theaters/nearby",
                params={"lat": 35.0, "lng": 139.0, "radius": 10.0},
            )

    assert r.status_code == 200
    theaters = r.json()["theaters"]
    assert theaters[0]["id"] == "172"
    assert theaters[0]["latitude"] == 35.68
    assert theaters[0]["longitude"] == 139.69
    # 2件目は詳細ページ取得失敗のため座標なし
    assert theaters[1]["id"] == "200"
    assert theaters[1]["latitude"] is None
    assert theaters[1]["longitude"] is None

    # 座標が SQLite キャッシュに永続化されている
    assert theaters_mod.coord_cache.get("172") == (35.68, 139.69)
    assert theaters_mod.coord_cache.get("200") is None
    # 住所がジオコーディングに渡された
    geoc.assert_called_once_with("東京都新宿区新宿3-1-1")


def test_movies_now_cached_second_call_not_scraped(client):
    """同一エンドポイントの2回目はキャッシュヒットし、スクレイパーは1回しか呼ばれない。"""
    with mock.patch("app.routers.movies.MovieListScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.parse.return_value = _movie_list_response()

        r1 = client.get("/api/movies/now")
        r2 = client.get("/api/movies/now")

    assert r1.status_code == 200
    assert r2.status_code == 200
    instance.fetch.assert_called_once()
    instance.parse.assert_called_once()


# --- バリデーションエラー（422） ---


def test_movie_detail_invalid_id_returns_422(client):
    # movie_id は数字のみ許可（^\d+$）
    r = client.get("/api/movies/abc")
    assert r.status_code == 422


def test_search_empty_q_returns_422(client):
    # q は 1〜200文字（空は不可）
    r = client.get("/api/search", params={"q": ""})
    assert r.status_code == 422


def test_search_too_long_q_returns_422(client):
    # q は最大200文字
    r = client.get("/api/search", params={"q": "a" * 201})
    assert r.status_code == 422


# --- エラー変換（スクレイパー例外 → HTTPステータス） ---


def test_not_found_error_maps_to_404(client):
    with mock.patch("app.routers.movies.MovieDetailScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.fetch.side_effect = FilmarksNotFoundError("ページが見つかりません")

        r = client.get("/api/movies/1001")

    assert r.status_code == 404


def test_unavailable_error_maps_to_503(client):
    with mock.patch("app.routers.movies.MovieListScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.fetch.side_effect = FilmarksUnavailableError(
            "Filmarks にアクセスできません"
        )

        r = client.get("/api/movies/now")

    assert r.status_code == 503


def test_parse_error_maps_to_500():
    """/api/movies/now でパース失敗（FilmarksParseError）は 500 に変換される。

    run_scrape が FilmarksError 系を 500 に変換する。TestClient は既定で
    サーバ例外（HTTPException 500）を再送出するため raise_server_exceptions=False
    を指定してレスポンスとして検証する。
    """
    with mock.patch("app.routers.movies.MovieListScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.fetch.side_effect = FilmarksParseError("HTMLのパースに失敗")

        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/movies/now")

    assert r.status_code == 500


def test_unexpected_error_maps_to_500():
    """予期しない例外（ValueError 等）も生の例外を漏らさず 500 に変換される。"""
    with mock.patch("app.routers.movies.MovieListScraper") as MockScraper:
        instance = MockScraper.return_value
        instance.fetch.side_effect = ValueError("意図しないエラー")

        client = TestClient(app, raise_server_exceptions=False)
        r = client.get("/api/movies/now")

    assert r.status_code == 500