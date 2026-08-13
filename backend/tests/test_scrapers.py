"""スクレイパー単体テスト（モックHTML / モッククライアント使用）。

実ネットワークには一切アクセスしない。
"""

import pytest

from app.models.movie import MovieListResponse
from app.scrapers.exceptions import FilmarksUnavailableError
from app.scrapers.list_scraper import MovieListScraper
from app.scrapers.movie_scraper import MovieDetailScraper
from app.scrapers.search_scraper import MovieSearchScraper
from app.scrapers.theater_scraper import (
    TheaterDetailScraper,
    TheaterListScraper,
    _time_key,
)
from tests import mock_html


# --- MovieListScraper ---


def test_movie_list_scraper_parses_cards(fake_client, make_soup):
    scraper = MovieListScraper(fake_client)
    soup = make_soup(mock_html.LIST_PAGE_HTML)
    response = scraper.parse(soup)

    assert isinstance(response, MovieListResponse)
    # 通常カード2枚（IDなしカードはスキップされる）
    assert len(response.results) == 2

    movie = response.results[0]
    assert movie.id == "1001"
    assert movie.title == "テスト映画A"
    assert movie.rating == 3.5
    assert movie.poster_url == "https://img.example.test/a.jpg"
    assert movie.release_date == "2026年08月01日"
    assert movie.genres == ["ドラマ", "SF"]
    assert movie.mark_count == 500
    assert movie.clip_count == 120

    # 評価が空のカード
    movie2 = response.results[1]
    assert movie2.id == "1002"
    assert movie2.rating is None


def test_movie_list_scraper_fetch_integrates(fake_client):
    """fetch() 経由（BaseScraper.fetch）でパースが成立すること。"""
    scraper = MovieListScraper(fake_client)
    response = scraper.parse(scraper.fetch("/list/now"))
    assert len(response.results) >= 1
    assert fake_client.calls == ["/list/now"]


def test_movie_list_scraper_empty_results(make_soup):
    scraper = MovieListScraper(client=None)
    soup = make_soup(mock_html.empty_list_page_html())
    response = scraper.parse(soup)

    assert response.results == []
    assert response.total == 0
    assert response.has_next is False


def test_fetch_detects_error_page(fake_client):
    """エラーページが fetch() で検出され例外になること。"""
    fake_client.pages["/list/now"] = mock_html.UNAVAILABLE_PAGE_HTML
    scraper = MovieListScraper(fake_client)
    with pytest.raises(FilmarksUnavailableError):
        scraper.fetch("/list/now")


# --- MovieDetailScraper ---


def test_movie_detail_scraper_parses(fake_client, make_soup):
    scraper = MovieDetailScraper(fake_client)
    soup = make_soup(mock_html.DETAIL_PAGE_HTML)
    detail = scraper.parse(soup)

    assert detail.id == "1001"
    assert detail.title == "テスト映画A"
    assert detail.original_title == "TEST MOVIE A"
    assert detail.synopsis == "これはあらすじです。"
    assert detail.rating == 3.5
    assert detail.review_count == 42  # JSON-LD の aggregateRating/reviewCount
    assert detail.release_date == "2026年08月01日"
    assert detail.runtime == "120分"
    assert detail.genres == ["SF", "ドラマ"]
    assert detail.director == ["山田監督"]
    assert detail.mark_count == 500
    assert detail.clip_count == 120
    assert detail.official_site == "https://www.example.test/official"


def test_movie_detail_cast_parsed(fake_client, make_soup):
    scraper = MovieDetailScraper(fake_client)
    soup = make_soup(mock_html.DETAIL_PAGE_HTML)
    detail = scraper.parse(soup)

    assert len(detail.cast) == 2
    assert detail.cast[0].name == "主演俳優"
    assert detail.cast[0].character == "主人公役"
    assert detail.cast[1].name == "脇役俳優"
    assert detail.cast[1].character is None


def test_movie_detail_streaming_parsed(fake_client, make_soup):
    """div.c2-list-vod を持つページでは配信情報がパースされる（回帰防止）。"""
    scraper = MovieDetailScraper(fake_client)
    soup = make_soup(mock_html.STREAMING_PAGE_HTML)
    detail = scraper.parse(soup)

    assert [s.service for s in detail.streaming] == [
        "U-NEXT",
        "Amazon Prime Video",
    ]
    assert detail.streaming[0].type == "見放題"
    assert detail.streaming[1].type == "見放題"


def test_movie_detail_streaming_empty_without_vod(fake_client, make_soup):
    """div.c2-list-vod が無いページでは配信情報は空になる。"""
    scraper = MovieDetailScraper(fake_client)
    soup = make_soup(mock_html.DETAIL_PAGE_HTML)
    detail = scraper.parse(soup)
    assert detail.streaming == []


# --- MovieSearchScraper ---


def test_movie_search_scraper_parses(fake_client, make_soup):
    scraper = MovieSearchScraper(fake_client, query="テスト", page=1)
    soup = make_soup(mock_html.SEARCH_PAGE_HTML)
    response = scraper.parse(soup)

    assert response.query == "テスト"
    assert response.heading == "テストに関する映画 3作品"
    assert len(response.results) == 1
    assert response.results[0].title == "検索結果映画"
    assert response.total == 3
    assert response.has_next is False  # 1 * 36 < 3 は偽


def test_movie_search_no_results(make_soup):
    scraper = MovieSearchScraper(client=None, query="存在しない", page=1)
    soup = make_soup(mock_html.empty_list_page_html())
    response = scraper.parse(soup)
    assert response.results == []
    assert response.query == "存在しない"


def test_time_key_extracts_hhmm():
    assert _time_key("2026-08-14T10:00:00+09:00") == "10:00"
    assert _time_key("2026-08-14T09:05:00+09:00") == "09:05"
    assert _time_key("13:30") == "13:30"
    # 抽出できない場合は元の値のまま（取りこぼし防止）
    assert _time_key("none") == "none"


# --- TheaterListScraper ---


def test_theater_list_fetch_prefecture_areas(fake_client):
    scraper = TheaterListScraper(fake_client)
    pref_name, areas = scraper.fetch_prefecture("tokyo")

    assert pref_name == "東京都"
    assert areas == [("99", "新宿"), ("134", "有楽町")]


def test_theater_list_parse_cards(fake_client, make_soup):
    scraper = TheaterListScraper(fake_client)
    soup = make_soup(mock_html.THEATER_AREA_HTML)
    theaters = scraper.parse(soup)

    assert len(theaters) == 2
    first = theaters[0]
    assert first.id == "172"
    assert first.name == "テストシネマ新宿"
    assert first.prefecture == "東京都"
    assert first.area_id == "99"
    assert first.url == "/theaters/tokyo/99/172"


def test_theater_list_fetch_area(fake_client):
    scraper = TheaterListScraper(fake_client)
    theaters = scraper.fetch_area("tokyo", "99")

    assert len(theaters) == 2
    # area_id がページ側で抽出できない場合も fetch_area で補完される
    for t in theaters:
        assert t.area_id == "99"


# --- TheaterDetailScraper ---


def test_theater_detail_parse_static(fake_client, make_soup):
    scraper = TheaterDetailScraper(fake_client)
    soup = make_soup(mock_html.THEATER_DETAIL_HTML)
    detail = scraper.parse(soup)

    assert detail.name == "テストシネマ新宿"
    assert detail.address == "東京都新宿区新宿3-1-1"
    assert detail.map_url == "https://maps.google.com/?q=テストシネマ新宿"
    assert detail.prefecture == "東京都"


def test_theater_detail_fetch_theater_with_schedule(fake_client):
    """静止HTML＋JSONスケジュールが合成されること。"""
    scraper = TheaterDetailScraper(fake_client)
    detail = scraper.fetch_theater("/theaters/tokyo/99/172")

    assert detail.id == "172"
    assert detail.area_id == "99"
    assert detail.url == "/theaters/tokyo/99/172"
    assert detail.name == "テストシネマ新宿"

    assert len(detail.movies) == 1
    movie = detail.movies[0]
    assert movie.movie_id == "3001"
    assert movie.movie_title == "スケジュール映画"
    assert movie.poster_url == "https://img.example.test/sched.jpg"
    # dates は1日以上、時刻が抽出・ソートされている
    dates = movie.dates
    assert len(dates) >= 1
    for times in dates.values():
        assert times == ["10:00", "13:30"]