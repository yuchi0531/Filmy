"""映画詳細ページ（/movies/{id}）のスクレイパー。"""

import json
import re

from bs4 import BeautifulSoup

from app.models.movie import CastMember, MovieDetail
from app.scrapers.base import BaseScraper
from app.scrapers.parser import parse_data_attr, to_float, to_int

_ID_RE = re.compile(r"/movies/(\d+)")


def _get_movie_ld_json(soup: BeautifulSoup) -> dict | None:
    """JSON-LD から Movie スキーマの dict を返す。"""
    for script in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") == "Movie":
            return data
    return None


def _strip_attr_quotes(value: str | None) -> str | None:
    """Vue 属性（:outline 等）の値の前後にある JSON 引用符を取り除く。"""
    if value is None:
        return None
    v = value.strip()
    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
        v = v[1:-1]
    return v


def _btn_count(soup: BeautifulSoup, selector: str, attr: str) -> int | None:
    """data-mark / data-clip 属性の count を返す（主対象は最初の要素）。"""
    el = soup.select_one(f"{selector}[{attr}]")
    if el is None:
        return None
    try:
        data = parse_data_attr(el, attr)
    except Exception:
        return None
    return to_int(data.get("count"))


def _info_value(soup: BeautifulSoup, label: str) -> str | None:
    """``ラベル：値`` 形式の h3 から値を取り出す。

    例: ``上映日：2026年07月31日`` → ``2026年07月31日``
    """
    for h3 in soup.select(
        "h3.p-content-detail__primary-info-title, "
        "h3.p-content-detail__secondary-info-title"
    ):
        text = h3.get_text(" ", strip=True)
        if text.startswith(label) and "：" in text:
            return text.split("：", 1)[1].strip() or None
    return None


def _ul_items(soup: BeautifulSoup, label: str) -> list[str]:
    """``label`` で始まる h3 の直後にある ul の li テキストを列挙する。"""
    for h3 in soup.select("h3"):
        if h3.get_text(" ", strip=True).startswith(label):
            ul = h3.find_next("ul")
            if ul is None:
                return []
            items: list[str] = []
            for li in ul.select("li"):
                a = li.find("a")
                text = a.get_text(" ", strip=True) if a else li.get_text(" ", strip=True)
                if text:
                    items.append(text)
            return items
    return []


def _movie_id(soup: BeautifulSoup, ld: dict | None) -> str | None:
    """正規化リンク・JSON-LD から映画IDを抽出する。"""
    canon = soup.select_one("link[rel='canonical']")
    if canon and canon.get("href"):
        m = _ID_RE.search(str(canon["href"]))
        if m:
            return m.group(1)
    if ld and ld.get("url"):
        m = _ID_RE.search(str(ld["url"]))
        if m:
            return m.group(1)
    return None


def _parse_streaming(soup: BeautifulSoup):
    """配信情報（可能なら）をパースする。

    現在の上映詳細ページでは VOD の実データが描画されないため、
    構造が揃った際にのみデータが入る（現状は空リスト）。
    """
    streaming = []
    container = soup.select_one("div.c2-list-vod")
    if container is None:
        return streaming
    for item in container.select(".js-btn-vod, li"):
        service = item.get("data-service") or item.get_text(" ", strip=True)
        if service:
            streaming.append(
                {
                    "service": str(service),
                    "type": item.get("data-type") or "",
                }
            )
    return streaming


class MovieDetailScraper(BaseScraper):
    """映画詳細ページのスクレイパー。:meth:`parse` は MovieDetail を返す。"""

    def parse(self, soup: BeautifulSoup) -> MovieDetail:
        ld = _get_movie_ld_json(soup)

        title_el = soup.select_one("h2.p-content-detail__title > span")
        title = title_el.get_text(" ", strip=True) if title_el else None

        original_el = soup.select_one("p.p-content-detail__original")
        original_title = (
            original_el.get_text(" ", strip=True) or None if original_el else None
        )

        # あらすじ: content-detail-synopsis の :outline 属性（後退: JSON-LD）
        synopsis = None
        syn_el = soup.select_one(
            "div#js-content-detail-synopsis content-detail-synopsis"
        )
        outline = syn_el.get(":outline") if syn_el is not None else None
        if outline is not None:
            synopsis = _strip_attr_quotes(str(outline))
        if not synopsis and ld:
            synopsis = ld.get("outline") or ld.get("description")

        rating_el = soup.select_one("div.c2-rating-l__text")
        rating = to_float(rating_el.get_text(" ", strip=True)) if rating_el else None

        poster = soup.select_one("div.c2-poster-l > img")
        poster_src = poster.get("src") if poster else None
        poster_url = str(poster_src) if poster_src is not None else None

        review_count = None
        if ld and ld.get("aggregateRating"):
            review_count = to_int(ld["aggregateRating"].get("reviewCount"))

        # 出演者
        cast = [
            CastMember(
                name=(
                    name_el.get_text(" ", strip=True)
                    if (name_el := h4.select_one(".c2-button-tertiary-s-multi-text__text"))
                    else h4.get_text(" ", strip=True)
                ),
                character=(
                    char_el.get_text(" ", strip=True)
                    if (char_el := h4.select_one(".c2-button-tertiary-s-multi-text__subtext"))
                    else None
                ),
            )
            for h4 in soup.select("div.p-people-list__casts h4.p-people-list__item")
            if h4.get_text(" ", strip=True)
        ]

        official_el = soup.select_one(
            "li.p-content-detail-links__item--official > a"
        )
        official_site = str(official_el["href"]) if official_el else None

        return MovieDetail(
            id=_movie_id(soup, ld) or "",
            title=title or "",
            original_title=original_title,
            rating=rating,
            review_count=review_count,
            poster_url=poster_url,
            release_date=_info_value(soup, "上映日"),
            genres=_ul_items(soup, "ジャンル"),
            mark_count=_btn_count(soup, "div.js-btn-mark", "data-mark"),
            clip_count=_btn_count(soup, "div.js-btn-clip", "data-clip"),
            synopsis=synopsis,
            runtime=_info_value(soup, "上映時間"),
            director=_ul_items(soup, "監督"),
            cast=cast,
            official_site=official_site,
            streaming=_parse_streaming(soup),
        )