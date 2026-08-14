"""劇場関連エンドポイント。

都道府県・エリア・劇場詳細・近隣検索を提供する。

実HTML構造に基づく対応:
- ``GET /api/theaters/{prefecture}`` は都道府県ページ（静止HTMLには劇場カードが無く
  エリア選択リンクのみ）から、その都道府県の **エリア一覧** を返す。
- ``GET /api/theaters/{prefecture}/{area_id}`` はエリアページ（劇場カードが静止HTMLに存在）
  から、そのエリアの **劇場一覧** を返す。
- ``GET /api/theaters/{prefecture}/{area_id}/{theater_id}`` は劇場詳細＋スケジュールを返す。
- ``GET /api/theaters/nearby`` は Filmarks の ``/pia_theaters`` JSON API（半径フィルタ済み・
  距離順）を利用して近隣劇場を返す。
"""

import json
import logging
import threading
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from fastapi import APIRouter, Path, Query

from app import geocode
from app.cache import cache_manager
from app.config import settings
from app.coord_cache import CoordCache
from app.models.theater import (
    AreaListResponse,
    AreaSummary,
    NearbyResponse,
    TheaterDetail,
    TheaterListResponse,
    TheaterSummary,
)
from app.routers.common import run_scrape
from app.scrapers.http_client import FilmarksClient
from app.scrapers.theater_scraper import (
    TheaterDetailScraper,
    TheaterListScraper,
    _THEATER_URL_RE,
)

router = APIRouter(prefix="/api/theaters", tags=["theaters"])

logger = logging.getLogger(__name__)

# エンドポイント間のキャッシュ名前空間
_CACHE_PREF = "theater_pref"
_CACHE_AREA = "theater_area"
_CACHE_DETAIL = "theater_detail"
_CACHE_NEARBY = "theater_nearby"

# 劇場座標の永続キャッシュ（SQLite）のモジュールレベルシングルトン。
# テストでは app.routers.theaters.coord_cache を monkeypatch して差し替える。
coord_cache = CoordCache(settings.coord_cache_path)

# 詳細ページの住所抽出セレクタ（Filmarks 実HTML構造）
_ADDRESS_SELECTOR = "div.p-theater-movies-info__address"


def _detail_path_from_url(url: str) -> str | None:
    """劇場URLから詳細ページのパス（``/theaters/{pref}/{area}/{id}``）を取り出す。

    - 相対パス（``/theaters/...`` で始まる）はそのまま返す。
    - 絶対URL（``https://filmarks.com/theaters/...``）は ``_THEATER_URL_RE`` の
      マッチ、またはURLパースの path から取り出す。
    """
    if url.startswith("/theaters/"):
        return url
    m = _THEATER_URL_RE.search(url)
    if m:
        return m.group(0)
    parsed = urlparse(url)
    if parsed.path.startswith("/theaters/"):
        return parsed.path
    return None


def _extract_address(html: str) -> str | None:
    """劇場詳細ページの HTML から住所テキストを抽出する。"""
    soup = BeautifulSoup(html, "lxml")
    el = soup.select_one(_ADDRESS_SELECTOR)
    if el is None:
        return None
    return el.get_text(" ", strip=True) or None


def _resolve_coords(client: FilmarksClient, theaters: list[TheaterSummary]) -> None:
    """近隣検索結果の各劇場に座標（緯度・経度）を補完する。

    1. 座標キャッシュ（SQLite）に座標があればそれを設定する。
    2. キャッシュに無い劇場は、詳細ページを ``get_html_batch`` で並列取得して
       住所を抽出 → ``geocode_addresses`` で並列ジオコーディング → キャッシュに保存する。
    3. 取得できない場合は ``latitude``/``longitude`` は None のままとする。
    """
    missing: list[tuple[TheaterSummary, str]] = []
    for t in theaters:
        coord = coord_cache.get(t.id)
        if coord is not None:
            t.latitude, t.longitude = coord
        elif t.url:
            path = _detail_path_from_url(t.url)
            if path:
                missing.append((t, path))

    if not missing:
        return

    htmls = client.get_html_batch([path for _, path in missing])
    # 住所抽出 → 並列ジオコーディング
    theater_addresses: list[tuple[TheaterSummary, str]] = []
    for (t, _path), html in zip(missing, htmls):
        if html is None:
            continue
        address = _extract_address(html)
        if not address:
            continue
        theater_addresses.append((t, address))

    if not theater_addresses:
        return

    coords = geocode.geocode_addresses([addr for _, addr in theater_addresses])
    for (t, address), coord in zip(theater_addresses, coords):
        if coord is None:
            continue
        latitude, longitude = coord
        t.latitude = latitude
        t.longitude = longitude
        coord_cache.set(t.id, latitude, longitude, address)


def _schedule_coord_resolution(theaters: list[TheaterSummary]) -> None:
    """未補完の劇場座標をバックグラウンドスレッドで補完する。

    - 詳細ページ取得（get_html_batch）とジオコーディングは FilmarksClient を
      新規生成して実行する（リクエスト処理と分離し、5秒スロットルは引き続き守られる）。
    - 補完結果は SQLite（coord_cache）に保存されるため、次回リクエストで反映される。
    - 失敗しても例外を握りつぶし、メインのレスポンスには影響させない。
    """
    def _task() -> None:
        try:
            with FilmarksClient() as client:
                _resolve_coords(client, theaters)
        except Exception:
            logger.warning("バックグラウンド座標補完に失敗しました", exc_info=True)

    threading.Thread(target=_task, daemon=True).start()


def _prefecture_list(prefecture: str) -> AreaListResponse:
    """都道府県ページから、その都道府県のエリア一覧を返す（キャッシュ24時間）。"""
    cached = cache_manager.get(_CACHE_PREF, prefecture)
    if cached is not None:
        return cached

    def scrape(client: FilmarksClient) -> AreaListResponse:
        scraper = TheaterListScraper(client)
        pref_name, areas = scraper.fetch_prefecture(prefecture)
        results = [
            AreaSummary(
                id=area_id,
                name=area_name,
                url=f"/theaters/{prefecture}/{area_id}",
            )
            for area_id, area_name in areas
        ]
        return AreaListResponse(
            prefecture=pref_name or prefecture,
            results=results,
            total=len(results),
        )

    result = run_scrape(scrape)
    cache_manager.set(_CACHE_PREF, prefecture, result, settings.cache_ttl_theater)
    return result


def _area_list(prefecture: str, area_id: str) -> TheaterListResponse:
    """エリアページから劇場一覧を返す（キャッシュ24時間）。"""
    key = f"{prefecture}:{area_id}"
    cached = cache_manager.get(_CACHE_AREA, key)
    if cached is not None:
        return cached

    def scrape(client: FilmarksClient) -> TheaterListResponse:
        scraper = TheaterListScraper(client)
        results = scraper.fetch_area(prefecture, area_id)
        pref_name = results[0].prefecture if results else prefecture
        return TheaterListResponse(
            prefecture=pref_name,
            results=results,
            total=len(results),
        )

    result = run_scrape(scrape)
    cache_manager.set(_CACHE_AREA, key, result, settings.cache_ttl_theater)
    return result


def _theater_detail(url_path: str, prefecture: str, area_id: str, theater_id: str) -> TheaterDetail:
    """劇場詳細＋スケジュールを返す（キャッシュ1時間）。

    キャッシュキーは prefecture/area_id/theater_id を含めることで、同一 theater_id を
    別の prefecture/area 経路から参照した場合のキャッシュ衝突を防ぐ。
    """
    key = f"{prefecture}:{area_id}:{theater_id}"
    cached = cache_manager.get(_CACHE_DETAIL, key)
    if cached is not None:
        return cached

    def scrape(client: FilmarksClient) -> TheaterDetail:
        scraper = TheaterDetailScraper(client)
        return scraper.fetch_theater(url_path)

    result = run_scrape(scrape)
    cache_manager.set(_CACHE_DETAIL, key, result, settings.cache_ttl_schedule)
    return result


def _nearby(lat: float, lng: float, radius_km: float) -> NearbyResponse:
    """近隣劇場を Filmarks の /pia_theaters JSON API で取得する（キャッシュ1時間）。

    Filmarks側がradiusフィルタ・距離順で返すため、ここでは距離計算はしない
    （座標が外部に公開されていないため）。distance_km は未設定とする。
    """
    key = f"{lat:.5f}:{lng:.5f}:{radius_km}"
    cached = cache_manager.get(_CACHE_NEARBY, key)
    if cached is not None:
        return cached

    # 座標補完が必要な劇場（バックグラウンドで補完する）
    pending: list[TheaterSummary] = []

    def scrape(client: FilmarksClient) -> NearbyResponse:
        path = (
            f"/pia_theaters?latitude={lat}&longitude={lng}"
            f"&radius={radius_km}"
        )
        raw = client.get_html(path)
        data = json.loads(raw)
        theaters: list[TheaterSummary] = []
        for p in data.get("piaTheaters", []) or []:
            tid = p.get("id")
            name = p.get("name")
            url = p.get("url")
            if tid is None or name is None:
                continue
            area_id = None
            if url:
                m = _THEATER_URL_RE.search(str(url))
                if m:
                    area_id = m.group(2)
            theaters.append(
                TheaterSummary(
                    id=str(tid),
                    name=str(name),
                    prefecture="近隣",
                    area_id=area_id,
                    url=str(url) if url else None,
                )
            )
        # 座標キャッシュ（SQLite）にある分だけ即時設定し、
        # 未補完の劇場はバックグラウンド補完に回す。
        for t in theaters:
            coord = coord_cache.get(t.id)
            if coord is not None:
                t.latitude, t.longitude = coord
            elif t.url and _detail_path_from_url(t.url):
                pending.append(t)
        return NearbyResponse(
            latitude=lat,
            longitude=lng,
            radius_km=radius_km,
            theaters=theaters,
        )

    result = run_scrape(scrape)

    if pending:
        # 未補完の劇場がある場合はバックグラウンドで補完し、今回はキャッシュしない
        # （次回リクエスト時に座標付きで応答・キャッシュする）。
        _schedule_coord_resolution(pending)
    else:
        # 全劇場の座標が揃っている場合のみキャッシュする
        cache_manager.set(_CACHE_NEARBY, key, result, settings.cache_ttl_schedule)
    return result


# L6: /nearby は /{prefecture} より先に登録する必要がある。
# 型パラメータを持つ /{prefecture} を先に登録すると "/nearby" が
# prefecture と解釈されるパス衝突が起きるため、ルート定義順が重要。
@router.get("/nearby", response_model=NearbyResponse)
def nearby(
    lat: float = Query(..., description="現在地の緯度"),
    lng: float = Query(..., description="現在地の経度"),
    radius: float = Query(10.0, ge=1, le=100, description="検索半径（km）"),
) -> NearbyResponse:
    """近隣劇場検索。半径1〜100km。"""
    return _nearby(lat, lng, radius)


@router.get("/{prefecture}", response_model=AreaListResponse)
def get_prefecture(prefecture: str = Path(...)) -> AreaListResponse:
    """都道府県別のエリア一覧。"""
    return _prefecture_list(prefecture)


@router.get(
    "/{prefecture}/{area_id}",
    response_model=TheaterListResponse,
)
def get_area(
    prefecture: str = Path(...),
    area_id: str = Path(..., pattern=r"^\d+$"),
) -> TheaterListResponse:
    """エリア別の劇場一覧。"""
    return _area_list(prefecture, area_id)


@router.get(
    "/{prefecture}/{area_id}/{theater_id}",
    response_model=TheaterDetail,
)
def get_theater(
    prefecture: str = Path(...),
    area_id: str = Path(..., pattern=r"^\d+$"),
    theater_id: str = Path(..., pattern=r"^\d+$"),
) -> TheaterDetail:
    """劇場詳細＋上映スケジュール。"""
    url_path = f"/theaters/{prefecture}/{area_id}/{theater_id}"
    return _theater_detail(url_path, prefecture, area_id, theater_id)