"""検索エンドポイント。"""

from urllib.parse import quote

from fastapi import APIRouter, Query

from app.cache import cache_manager
from app.config import settings
from app.models.movie import MovieListResponse
from app.routers.common import run_scrape
from app.scrapers.http_client import FilmarksClient
from app.scrapers.search_scraper import MovieSearchScraper

router = APIRouter(prefix="/api/search", tags=["search"])

_CACHE_NAMESPACE_SEARCH = "search"


@router.get("", response_model=MovieListResponse)
def search(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="検索キーワード（1〜200文字）",
    ),
    page: int = Query(1, ge=1, description="ページ番号（1始まり）"),
) -> MovieListResponse:
    """映画検索。キャッシュ → なければスクレイピング → キャッシュ保存。

    ページごとにキャッシュキーを分ける（``q:page``）。
    """
    key = f"{q}:{page}"
    cached = cache_manager.get(_CACHE_NAMESPACE_SEARCH, key)
    if cached is not None:
        return cached

    path = f"/search/movies?q={quote(q)}"
    if page > 1:
        path += f"&page={page}"

    def scrape(client: FilmarksClient) -> MovieListResponse:
        scraper = MovieSearchScraper(client, query=q, page=page)
        return scraper.parse(scraper.fetch(path))

    result = run_scrape(scrape)
    cache_manager.set(
        _CACHE_NAMESPACE_SEARCH, key, result, settings.cache_ttl_search
    )
    return result
