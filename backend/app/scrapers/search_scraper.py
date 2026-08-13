"""映画検索ページ（/search/movies?q=...）のスクレイパー。

検索結果は映画一覧ページと同じカード構造（div.js-cassette）なので、
``list_scraper`` の共通ヘルパーを再利用してパースする。
"""

from bs4 import BeautifulSoup

from app.models.movie import MovieListResponse
from app.scrapers.base import BaseScraper
from app.scrapers.list_scraper import (
    _has_next,
    _heading_text,
    _heading_total,
    parse_movie_summary,
)


class MovieSearchScraper(BaseScraper):
    """映画検索ページのスクレイパー。

    ``query`` はレスポンスの ``query`` フィールドに、``page`` は ``page`` と
    ``has_next`` フィールドに反映される。
    """

    def __init__(
        self, client, query: str | None = None, page: int = 1
    ) -> None:
        super().__init__(client)
        self.query = query
        self.page = max(1, page)

    def parse(self, soup: BeautifulSoup) -> MovieListResponse:
        heading = _heading_text(soup)
        results = [
            item
            for card in soup.select("div.p-contents-grid > div.js-cassette")
            if (item := parse_movie_summary(card)) is not None
        ]
        total = _heading_total(heading) or len(results)
        return MovieListResponse(
            query=self.query,
            heading=heading,
            results=results,
            total=total,
            page=self.page,
            has_next=_has_next(self.page, total, results),
        )