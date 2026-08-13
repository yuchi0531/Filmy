"""Filmarks スクレイピング基盤。

公開API:
- :class:`FilmarksClient` — HTTPクライアント
- :class:`BaseScraper` — スクレイピング基底クラス
- 例外: ``FilmarksError``, ``FilmarksUnavailableError``,
  ``FilmarksNotFoundError``, ``FilmarksParseError``
- ヘルパー: ``check_error_page``, ``parse_data_attr``
"""

from app.scrapers.base import BaseScraper
from app.scrapers.exceptions import (
    FilmarksError,
    FilmarksNotFoundError,
    FilmarksParseError,
    FilmarksUnavailableError,
)
from app.scrapers.http_client import FilmarksClient
from app.scrapers.list_scraper import MovieListScraper, parse_movie_summary
from app.scrapers.movie_scraper import MovieDetailScraper
from app.scrapers.parser import check_error_page, parse_data_attr
from app.scrapers.search_scraper import MovieSearchScraper
from app.scrapers.theater_scraper import TheaterDetailScraper, TheaterListScraper

__all__ = [
    "BaseScraper",
    "FilmarksClient",
    "FilmarksError",
    "FilmarksNotFoundError",
    "FilmarksParseError",
    "FilmarksUnavailableError",
    "check_error_page",
    "parse_data_attr",
    "MovieListScraper",
    "MovieDetailScraper",
    "MovieSearchScraper",
    "parse_movie_summary",
    "TheaterListScraper",
    "TheaterDetailScraper",
]
