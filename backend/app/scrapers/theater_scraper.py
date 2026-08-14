"""劇場（/theaters）関連のスクレイパー。

実HTML構造（2026-08-14 確認）に基づく:

- 都道府県ページ ``/theaters/{pref}``（例 ``/theaters/tokyo``）の静止HTMLには
  劇場カードは無く、**エリア選択リンク**だけを持つ
  （``a.p-content-schedule-select-item__link`` → ``/theaters/{pref}/{area_id}``、テキスト「新宿(4)」）。
- エリアページ ``/theaters/{pref}/{area_id}``（例 ``/theaters/tokyo/99``）で
  初めて**劇場カード**が静止HTMLに存在する:
  ``div.p-theater-card__theater.js-theater-card``（``data-theater-id``）、
  内 ``a[href="/theaters/{pref}/{area}/{theater_id}"]``、``h3.p-theater-card__theater-name``。
- 劇場詳細ページ静止部: ``name=div.p-theater-movies-info__name``、
  ``address=div.p-theater-movies-info__address``、
  ``map=div.p-theater-movies-info__map > a[href]``（Google Maps検索URL）。
- 上映スケジュール・上映中映画は静止HTMLに無く、同一ホストの **JSON API** が提供する:
  ``GET /pia_theaters/{id}/movies?schedule_date=YYYY-MM-DD`` と
  ``GET /pia_theaters/{id}/recent/movies``。
"""

import json
import re
from datetime import date, timedelta

from bs4 import BeautifulSoup, Tag

from app.models.theater import (
    MovieSchedule,
    TheaterDetail,
    TheaterSummary,
)
from app.scrapers.base import BaseScraper

# 劇場ID（最終セグメント）抽出用
_THEATER_URL_RE = re.compile(r"/theaters/([^/]+)/(\d+)/(\d+)")

# エリアリンク例: 新宿(4)
_AREA_TEXT_RE = re.compile(r"^(.*?)\s*\((\d+)\)\s*$")


# 上映時刻の "HH:MM" 抽出用。完全タイムスタンプ（例 "2026-08-14T10:00:00+09:00"）や
# プレーンな "10:00" のどちらにも対応する。
_TIME_RE = re.compile(r"(?:^|\D)(\d{1,2}):(\d{2})(?:\D|$)")


def _time_key(start: str) -> str:
    """”start” 値から時刻部分（"HH:MM"）を抽出し、ソート用の正規化文字列を返す。

    - 完全タイムスタンプ「2026-08-14T10:00:00+09:00」→ "10:00" を抽出
    - プレーンな「10:00」→ そのまま
    - 抽出できない場合は元の値をそのまま返す（取り残しを防ぐ）
    """
    m = _TIME_RE.search(start)
    if m:
        hour = int(m.group(1))
        return f"{hour:02d}:{m.group(2)}"
    return start


def _area_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """都道府県ページのエリア選択リンクから ``(area_id, エリア名)`` のリストを返す。

    例: ``a.p-content-schedule-select-item__link`` の href ``/theaters/tokyo/99``
    とテキスト「新宿(4)」から ``("99", "新宿")`` を得る。
    """
    areas: list[tuple[str, str]] = []
    for a in soup.select("a.p-content-schedule-select-item__link[href]"):
        href = str(a.get("href") or "")
        m = re.search(r"/theaters/[^/]+/(\d+)", href)
        if not m:
            continue
        area_id = m.group(1)
        text = a.get_text(" ", strip=True)
        name = text
        am = _AREA_TEXT_RE.match(text)
        if am:
            name = am.group(1).strip()
        if name and (area_id, name) not in areas:
            areas.append((area_id, name))
    return areas


def _theater_id_from_link(link: Tag) -> str | None:
    """劇場カードから劇場IDを抽出する（data-theater-id または href 最終セグメント）。"""
    tid = link.get("data-theater-id")
    if tid is not None and str(tid) != "":
        return str(tid)
    a = link.select_one("a[href]")
    if a and a.get("href"):
        m = _THEATER_URL_RE.search(str(a["href"]))
        if m:
            return m.group(3)
    return None


def _theater_url_from_link(link: Tag) -> str | None:
    a = link.select_one("a[href]")
    if a and a.get("href"):
        href = str(a["href"])
        if href.startswith("/theaters/"):
            return href
    return None


def _theater_cards(soup: BeautifulSoup) -> list[Tag]:
    return soup.select("div.p-theater-card__theater.js-theater-card")


def _summary_from_card(card: Tag, prefecture: str, area_id: str | None,) -> TheaterSummary | None:
    """1枚の劇場カード（div.p-theater-card__theater）を TheaterSummary にパースする。"""
    theater_id = _theater_id_from_link(card)
    if theater_id is None:
        return None
    name_el = card.select_one("h3.p-theater-card__theater-name")
    name_text = name_el.get_text(" ", strip=True) if name_el else ""
    return TheaterSummary(
        id=theater_id,
        name=name_text or "",
        prefecture=prefecture,
        area_id=area_id,
        url=_theater_url_from_link(card),
    )


def _prefecture_from_heading(soup: BeautifulSoup) -> str:
    """h1 見出し（例「東京都の映画館：…」）から都道府県名を抽出する。"""
    for sel in ("h1.c-heading-1", "h1.c-page-title__title", "h1"):
        el = soup.select_one(sel)
        if el:
            text = el.get_text(" ", strip=True)
            # 「東京都の映画館: 上映中…」の「の映画館」まで
            m = re.split(r"の映画館", text, maxsplit=1)
            if m and m[0].strip():
                return m[0].strip()
            return text or ""
    return ""


def _prefecture_from_breadcrumb(soup: BeautifulSoup) -> str:
    """JSON-LD BreadcrumbList から都道府県名を抽出する。

    都道府県ページの見出し（例「有楽町の映画館」）は都道府県名を持たないため、
    エリア・詳細ページではパンくずの「東京都の映画館」等から都道府県名を得る。
    """
    for script in soup.select("script[type='application/ld+json']"):
        raw = script.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if not isinstance(data, dict) or data.get("@type") != "BreadcrumbList":
            continue
        for item in data.get("itemListElement", []) or []:
            name = (item.get("item") or {}).get("name") if isinstance(item, dict) else None
            if not name or not isinstance(name, str):
                continue
            m = re.match(r"^(.*?)の映画館$", name.strip())
            if m and m.group(1).strip():
                return m.group(1).strip()
    return ""


def _prefecture_for(soup: BeautifulSoup) -> str:
    """ページから都道府県名を抽出する（パンくず優先）。

    エリア・詳細ページのh1は「有楽町の映画館」等で都道府県名を持たず、
    パンくずJSON-LD（最初の「○○の映画館」）が確実に都道府県名を提供する。
    """
    return _prefecture_from_breadcrumb(soup) or _prefecture_from_heading(soup)


class TheaterListScraper(BaseScraper):
    """劇場一覧のスクレイパー。

    - ``fetch_prefecture(prefecture)``: ``/theaters/{prefecture}`` の都道府県ページから
      都道府県名＋エリア一覧を返す。
    - ``fetch_area(prefecture, area_id)``: ``/theaters/{prefecture}/{area_id}`` の
      エリアページから劇場カード一覧を返す。
    - ``parse(soup)``: 劇場カード（エリアページ）を ``list[TheaterSummary]`` にパースする。
    """

    def parse(self, soup: BeautifulSoup) -> list[TheaterSummary]:
        """劇場カードをパースする（エリアページ用）。"""
        prefecture = _prefecture_for(soup)
        results: list[TheaterSummary] = []
        for card in _theater_cards(soup):
            area_id = None
            url = _theater_url_from_link(card)
            if url:
                m = _THEATER_URL_RE.search(url)
                if m:
                    area_id = m.group(2)
            item = _summary_from_card(card, prefecture, area_id)
            if item is not None:
                results.append(item)
        return results

    def fetch_prefecture(self, prefecture: str) -> tuple[str, list[tuple[str, str]]]:
        """都道府県ページを取得し ``(都道府県名, [(area_id, エリア名), ...])`` を返す。"""
        soup = self.fetch(f"/theaters/{prefecture}")
        name = _prefecture_for(soup) or _prefecture_from_heading(soup)
        areas = _area_links(soup)
        return name, areas

    def fetch_area(
        self, prefecture: str, area_id: str
    ) -> list[TheaterSummary]:
        """エリアページを取得し劇場カードを ``list[TheaterSummary]`` で返す。"""
        soup = self.fetch(f"/theaters/{prefecture}/{area_id}")
        results = self.parse(soup)
        for item in results:
            if item.area_id is None:
                item.area_id = area_id
        return results


class TheaterDetailScraper(BaseScraper):
    """劇場詳細＋スケジュールのスクレイパー。

    ``fetch_theater(url_path)`` で詳細ページを取得し、静止HTML（名前・住所・地図URL）と
    JSON API（上映中映画＋日付別スケジュール）を合成して ``TheaterDetail`` を返す。
    """

    def __init__(self, client, schedule_days: int = 7) -> None:
        super().__init__(client)
        # スケジュールを取得する日数（今日から schedule_days 日分）。
        # 共有スロットル（プロセス共有5秒）がリクエスト毎に直列化するため、
        # 7日分の取得は初回に約40秒かかるが、キャッシュTTLを24時間に延長
        # しているため再取得頻度は低い。Filmarksは毎週火曜更新のため鮮度も十分。
        self.schedule_days = max(1, schedule_days)

    def _fetch_json(self, path: str) -> dict:
        """JSON API のレスポンスを dict で返す。"""
        raw = self.client.get_html(path)
        return json.loads(raw)

    def parse(self, soup: BeautifulSoup) -> TheaterDetail:
        """詳細ページの静止HTML部分（名前・住所・地図URL等）を TheaterDetail にパースする。

        座標はFilmarks側に存在しないため latitude/longitude は None のまま。
        スケジュールは :meth:`fetch_theater` 側で JSON から補完する。
        """
        name = None
        el = soup.select_one("div.p-theater-movies-info__name")
        if el:
            name = el.get_text(" ", strip=True) or None

        address = None
        el = soup.select_one("div.p-theater-movies-info__address")
        if el:
            address = el.get_text(" ", strip=True) or None

        map_url = None
        el = soup.select_one("a.p-theater-movies-info__map[href]")
        if el and el.get("href"):
            map_url = str(el["href"])

        prefecture = _prefecture_for(soup)

        return TheaterDetail(
            id="",
            name=name or "",
            prefecture=prefecture,
            address=address,
            map_url=map_url,
        )

    def fetch_theater(self, url_path: str) -> TheaterDetail:
        """劇場詳細ページを取得し、静止HTML＋JSONスケジュールを合成して返す。

        ``url_path`` 例: ``/theaters/tokyo/134/172``
        """
        soup = self.fetch(url_path)
        detail = self.parse(soup)

        m = _THEATER_URL_RE.search(url_path)
        if not m:
            raise ValueError(f"劇場URLを解釈できません: {url_path}")
        prefecture_slug, area_id, theater_id = m.group(1), m.group(2), m.group(3)

        detail.id = theater_id
        if detail.area_id is None:
            detail.area_id = area_id
        if detail.url is None:
            detail.url = f"/theaters/{prefecture_slug}/{area_id}/{theater_id}"

        detail.movies = self._fetch_schedule(theater_id)
        return detail

    def _fetch_schedule(self, theater_id: str) -> list[MovieSchedule]:
        """JSON API から上映中映画と日付別スケジュールを取得し MovieSchedule のリストで返す。"""
        movies: dict[str, MovieSchedule] = {}

        today = date.today()
        for i in range(self.schedule_days):
            day = today + timedelta(days=i)
            date_str = day.isoformat()
            try:
                data = self._fetch_json(
                    f"/pia_theaters/{theater_id}/movies?schedule_date={date_str}"
                )
            except Exception:
                continue
            for mv in data.get("movies", []) or []:
                mid = mv.get("id")
                if mid is None:
                    continue
                key = str(mid)
                ms = movies.get(key)
                if ms is None:
                    ms = MovieSchedule(
                        movie_id=key,
                        movie_title=str(mv.get("title") or ""),
                        poster_url=(mv.get("imagePath") or None),
                    )
                    movies[key] = ms
                times: list[str] = []
                for screen in mv.get("screens", []) or []:
                    for st in screen.get("showtimes", []) or []:
                        start = st.get("start")
                        if start:
                            # L5: start は完全タイムスタンプの場合があるため、
                            # 時刻部分（"HH:MM"）を抽出してからソートする
                            times.append(_time_key(str(start)))
                if times:
                    ms.dates[date_str] = sorted(set(times))

        # キー順（映画ID順）で安定させる
        return [movies[k] for k in sorted(movies.keys())]