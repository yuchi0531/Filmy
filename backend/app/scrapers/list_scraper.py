"""映画一覧ページ（/list/now 等）のスクレイパー。

共通のカードパースヘルパー（`_parse_card` / `_heading_text` / `_heading_total`）も
ここに置き、検索スクレイパー（search_scraper）から再利用する。
"""

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.models.movie import MovieListResponse, MovieSummary
from app.scrapers.base import BaseScraper
from app.scrapers.parser import parse_data_attr, to_int

# 映画IDを抽出するためのリンクパターン: /movies/{id}
_ID_LINK_RE = re.compile(r"/movies/(\d+)")

# Filmarks の1ページあたりの表示件数（実HTMLで検証済み: /list/* と /search 共通）
PAGE_SIZE = 36


def _extract_id(card: Tag) -> str | None:
    """カードから映画IDを抽出する。

    ``data-mark`` / ``data-clip`` の ``movie_id`` フィールド、または
    カード内リンク（``/movies/{id}``）から取得する。
    """
    for attr in ("data-mark", "data-clip"):
        try:
            data = parse_data_attr(card, attr)
        except Exception:
            continue
        movie_id = data.get("movie_id")
        if movie_id is not None:
            return str(movie_id)
    # リンクからのフォールバック
    link = card.select_one("a[href*='/movies/']")
    if link and link.get("href"):
        m = _ID_LINK_RE.search(str(link["href"]))
        if m:
            return m.group(1)
    return None


def _extract_count(card: Tag, attr: str) -> int | None:
    """``data-mark`` / ``data-clip`` の ``count`` フィールドを安全に返す。"""
    try:
        data = parse_data_attr(card, attr)
    except Exception:
        return None
    count = data.get("count")
    # 数値文字列でない場合は None（安全な変換）
    return to_int(count)


def _text(selector: str, card: Tag) -> str | None:
    el = card.select_one(selector)
    if el is None:
        return None
    text = el.get_text(" ", strip=True)
    return text or None


def parse_movie_summary(card: Tag) -> MovieSummary | None:
    """1枚の映画カード（div.js-cassette）を MovieSummary にパースする。"""
    movie_id = _extract_id(card)
    if movie_id is None:
        return None

    title = _text("h3.p-content-cassette__title", card)

    rating_text = _text("div.c-rating__score", card)
    rating = None
    if rating_text:
        try:
            rating = float(rating_text)
        except ValueError:
            rating = None

    poster = card.select_one("div.c2-poster-m > img")
    poster_src = poster.get("src") if poster else None
    poster_url: str | None = str(poster_src) if poster_src is not None else None

    # 公開日（上映日）: 「上映日：」の次にある span
    release_date = None
    release_span = None
    for h4 in card.select("h4.p-content-cassette__other-info-title"):
        if h4.get_text(strip=True).startswith("上映日"):
            release_span = h4.find_next_sibling("span")
            break
    if release_span is not None:
        release_date = release_span.get_text(" ", strip=True) or None

    # ジャンル: ul.genres 内の a テキスト
    genres: list[str] = []
    for a in card.select("ul.genres li a"):
        text = a.get_text(" ", strip=True)
        if text:
            genres.append(text)

    return MovieSummary(
        id=movie_id,
        title=title or "",
        rating=rating,
        poster_url=poster_url,
        release_date=release_date,
        genres=genres,
        mark_count=_extract_count(card, "data-mark"),
        clip_count=_extract_count(card, "data-clip"),
    )


def _heading_text(soup: BeautifulSoup) -> str | None:
    """ページ見出しを返す（h1.c-heading-1 または h1.c-page-title__title）。"""
    for sel in ("h1.c-heading-1", "h1.c-page-title__title"):
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            return text or None
    return None


def _heading_total(heading: str | None) -> int | None:
    """見出し末尾の「459作品」等から件数を抽出する。"""
    if not heading:
        return None
    m = re.search(r"(\d[\d,]*)\s*作品", heading)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def _has_next(page: int, total: int, results: list) -> bool:
    """次ページの有無を返す。

    総件数が取得できている場合は ``page * PAGE_SIZE < total`` で判定する。
    取得できない場合は「当該ページが1ページ分埋まっているか」でフォールバックする。
    """
    if total > 0:
        return page * PAGE_SIZE < total
    return len(results) >= PAGE_SIZE


class MovieListScraper(BaseScraper):
    """映画一覧ページ（上映中・公開予定・トレンド等）のスクレイパー。"""

    def __init__(self, client, page: int = 1) -> None:
        super().__init__(client)
        self.page = max(1, page)

    def parse(self, soup: BeautifulSoup) -> MovieListResponse:
        heading = _heading_text(soup)
        results: list[MovieSummary] = []
        for card in soup.select("div.p-contents-grid > div.js-cassette"):
            item: Any = parse_movie_summary(card)
            if item is not None:
                results.append(item)
        total = _heading_total(heading) or len(results)
        return MovieListResponse(
            heading=heading,
            results=results,
            total=total,
            page=self.page,
            has_next=_has_next(self.page, total, results),
        )