"""app/models/movie.py と app/models/theater.py のテスト。"""

import pytest
from pydantic import ValidationError

from app.models.movie import (
    CastMember,
    MovieDetail,
    MovieListResponse,
    MovieSummary,
    StreamingInfo,
)
from app.models.theater import (
    AreaListResponse,
    AreaSummary,
    MovieSchedule,
    NearbyResponse,
    TheaterDetail,
    TheaterListResponse,
    TheaterSummary,
)


# --- MovieSummary / MovieDetail ---


def test_movie_summary_minimal():
    m = MovieSummary(id="1", title="映画")
    assert m.id == "1"
    assert m.title == "映画"
    assert m.original_title is None
    assert m.rating is None
    assert m.review_count is None
    assert m.genres == []  # Field(default_factory=list)
    assert m.mark_count is None
    assert m.clip_count is None


def test_movie_summary_full():
    m = MovieSummary(
        id="1",
        title="映画",
        original_title="MOVIE",
        rating=3.5,
        review_count=100,
        poster_url="https://example.com/p.jpg",
        release_date="2026年08月01日",
        genres=["ドラマ"],
        mark_count=500,
        clip_count=120,
    )
    assert m.rating == 3.5
    assert m.review_count == 100
    assert m.genres == ["ドラマ"]


def test_movie_summary_rating_coerced_from_str():
    m = MovieSummary(id="1", title="映画", rating="3.5")
    assert m.rating == 3.5


def test_movie_detail_inherits_summary_and_defaults():
    d = MovieDetail(id="1", title="映画")
    assert isinstance(d, MovieSummary)
    assert d.synopsis is None
    assert d.runtime is None
    assert d.director == []
    assert d.cast == []
    assert d.streaming == []
    assert d.official_site is None


def test_movie_detail_nested_models():
    d = MovieDetail(
        id="1",
        title="映画",
        cast=[CastMember(name="俳優", character="役名")],
        streaming=[StreamingInfo(service="netflix", type="見放題")],
        director=["監督A"],
    )
    assert d.cast[0].name == "俳優"
    assert d.cast[0].character == "役名"
    assert d.streaming[0].service == "netflix"
    assert d.director == ["監督A"]


def test_cast_member_character_optional():
    c = CastMember(name="俳優")
    assert c.character is None


def test_casting_invalid_name_raises():
    with pytest.raises(ValidationError):
        CastMember(name=123)


def test_movie_list_response_defaults():
    resp = MovieListResponse(results=[], total=0)
    assert resp.query is None
    assert resp.heading is None
    assert resp.page == 1
    assert resp.has_next is False
    assert resp.results == []


def test_movie_list_response_with_results():
    resp = MovieListResponse(
        query="q", results=[MovieSummary(id="1", title="t")], total=1
    )
    assert resp.total == 1
    assert resp.results[0].id == "1"


# --- theater models ---


def test_movie_schedule_dates_default_dict():
    s = MovieSchedule(movie_id="1", movie_title="映画")
    assert s.dates == {}
    assert s.poster_url is None


def test_movie_schedule_with_dates():
    s = MovieSchedule(
        movie_id="1",
        movie_title="映画",
        poster_url="https://e.com/p.jpg",
        dates={"2026-08-14": ["10:00", "13:00"]},
    )
    assert s.dates["2026-08-14"] == ["10:00", "13:00"]


def test_theater_summary_required_fields():
    t = TheaterSummary(id="1", name="劇場", prefecture="東京都")
    assert t.area_id is None
    assert t.url is None
    assert t.distance_km is None


def test_theater_summary_missing_prefecture_raises():
    with pytest.raises(ValidationError):
        TheaterSummary(id="1", name="劇場")


def test_theater_detail_inherits_and_defaults():
    d = TheaterDetail(id="1", name="劇場", prefecture="東京都")
    assert isinstance(d, TheaterSummary)
    assert d.latitude is None
    assert d.longitude is None
    assert d.map_url is None
    assert d.movies == []


def test_area_summary():
    a = AreaSummary(id="99", name="新宿", theater_count=4, url="/theaters/tokyo/99")
    assert a.theater_count == 4


def test_area_list_response():
    resp = AreaListResponse(
        prefecture="東京都",
        results=[AreaSummary(id="99", name="新宿")],
        total=1,
    )
    assert resp.total == 1


def test_theater_list_response():
    resp = TheaterListResponse(
        prefecture="東京都",
        results=[TheaterSummary(id="1", name="劇場", prefecture="東京都")],
        total=1,
    )
    assert resp.results[0].id == "1"


def test_nearby_response():
    resp = NearbyResponse(
        latitude=35.68,
        longitude=139.69,
        radius_km=10.0,
        theaters=[TheaterSummary(id="1", name="劇場", prefecture="近隣")],
    )
    assert resp.latitude == 35.68
    assert resp.radius_km == 10.0
    assert resp.theaters[0].prefecture == "近隣"