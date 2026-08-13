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

from fastapi import APIRouter, Path, Query

from app.cache import cache_manager
from app.config import settings
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
from app.scrapers.theater_scraper import TheaterDetailScraper, TheaterListScraper

router = APIRouter(prefix="/api/theaters", tags=["theaters"])

# エンドポイント間のキャッシュ名前空間
_CACHE_PREF = "theater_pref"
_CACHE_AREA = "theater_area"
_CACHE_DETAIL = "theater_detail"
_CACHE_NEARBY = "theater_nearby"


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


def _theater_detail(url_path: str, theater_id: str) -> TheaterDetail:
    """劇場詳細＋スケジュールを返す（キャッシュ1時間）。"""
    cached = cache_manager.get(_CACHE_DETAIL, theater_id)
    if cached is not None:
        return cached

    def scrape(client: FilmarksClient) -> TheaterDetail:
        scraper = TheaterDetailScraper(client)
        return scraper.fetch_theater(url_path)

    result = run_scrape(scrape)
    cache_manager.set(_CACHE_DETAIL, theater_id, result, settings.cache_ttl_schedule)
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

    def scrape(client: FilmarksClient) -> NearbyResponse:
        path = (
            f"/pia_theaters?latitude={lat}&longitude={lng}"
            f"&radius={radius_km}"
        )
        import json

        from app.scrapers.theater_scraper import _THEATER_URL_RE

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
        return NearbyResponse(
            latitude=lat,
            longitude=lng,
            radius_km=radius_km,
            theaters=theaters,
        )

    result = run_scrape(scrape)
    # M1: 近隣検索は位置情報ベースのため鮮度が重要。劇場一覧(24h)ではなく
    # schedule(1h) と同じ TTL でキャッシュする。
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
    return _theater_detail(url_path, theater_id)