"""映画関連エンドポイント。"""

from fastapi import APIRouter, Path, Query

from app.cache import cache_manager
from app.config import settings
from app.models.movie import MovieDetail, MovieListResponse
from app.routers.common import run_scrape
from app.scrapers.http_client import FilmarksClient
from app.scrapers.list_scraper import MovieListScraper
from app.scrapers.movie_scraper import MovieDetailScraper

router = APIRouter(prefix="/api/movies", tags=["movies"])

# 一覧エンドポイント名 → スクレイピング対象の Filmarks パス
_LIST_PATHS: dict[str, str] = {
    "now": "/list/now",
    "coming": "/list/coming",
    "upcoming": "/list/upcoming",
    "trend": "/list/trend",
}

_CACHE_NAMESPACE_LIST = "movie_list"
_CACHE_NAMESPACE_DETAIL = "movie_detail"


def _movie_list(endpoint: str, page: int) -> MovieListResponse:
    """キャッシュ → なければスクレイピング → キャッシュ保存 の一覧取得。

    ページごとにキャッシュキーを分ける（``endpoint:page``）。
    """
    key = f"{endpoint}:{page}"
    cached = cache_manager.get(_CACHE_NAMESPACE_LIST, key)
    if cached is not None:
        return cached

    path = _LIST_PATHS[endpoint]
    if page > 1:
        path = f"{path}?page={page}"

    def scrape(client: FilmarksClient) -> MovieListResponse:
        scraper = MovieListScraper(client, page=page)
        return scraper.parse(scraper.fetch(path))

    result = run_scrape(scrape)
    cache_manager.set(
        _CACHE_NAMESPACE_LIST, key, result, settings.cache_ttl_movie_list
    )
    return result


@router.get("/now", response_model=MovieListResponse)
def now(page: int = Query(1, ge=1)) -> MovieListResponse:
    """上映中映画一覧（ページング対応）。"""
    return _movie_list("now", page)


@router.get("/coming", response_model=MovieListResponse)
def coming(page: int = Query(1, ge=1)) -> MovieListResponse:
    """公開予定映画一覧（ページング対応）。"""
    return _movie_list("coming", page)


@router.get("/upcoming", response_model=MovieListResponse)
def upcoming(page: int = Query(1, ge=1)) -> MovieListResponse:
    """今週公開映画一覧（ページング対応）。"""
    return _movie_list("upcoming", page)


@router.get("/trend", response_model=MovieListResponse)
def trend(page: int = Query(1, ge=1)) -> MovieListResponse:
    """トレンド映画一覧（ページング対応）。"""
    return _movie_list("trend", page)


@router.get("/{movie_id}", response_model=MovieDetail)
def get_movie(movie_id: str = Path(..., pattern=r"^\d+$")) -> MovieDetail:
    """映画詳細。キャッシュ → なければスクレイピング → キャッシュ保存。"""
    cached = cache_manager.get(_CACHE_NAMESPACE_DETAIL, movie_id)
    if cached is not None:
        return cached

    path = f"/movies/{movie_id}"

    def scrape(client: FilmarksClient) -> MovieDetail:
        scraper = MovieDetailScraper(client)
        return scraper.parse(scraper.fetch(path))

    result = run_scrape(scrape)
    cache_manager.set(
        _CACHE_NAMESPACE_DETAIL, movie_id, result, settings.cache_ttl_movie_detail
    )
    return result
