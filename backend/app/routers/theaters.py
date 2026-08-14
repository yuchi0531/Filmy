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
import time
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

# L3: 都道府県スラッグのパスパラメータ制約。Filmarks URL とキャッシュキーに
# そのまま埋め込まれるため、小文字英数字・ハイフンのみ許可する。
_PREFECTURE_PATTERN = r"^[a-z0-9\-]+$"

# エンドポイント間のキャッシュ名前空間
_CACHE_PREF = "theater_pref"
_CACHE_AREA = "theater_area"
_CACHE_DETAIL = "theater_detail"
_CACHE_NEARBY = "theater_nearby"
# 座標未解決時の短TTL（30秒）キャッシュ用の別名前空間。
# CacheManager は同一名前空間で TTL が変わると TTLCache を作り直して全エントリを
# 破棄するため、正規キャッシュ（1時間）と同じ `theater_nearby` を使うと、短TTLと
# 正規TTLが交互に発生して互いの全エントリをフラッシュし合う（C1）。名前空間を
# 分離することで、短TTLキャッシュと正規キャッシュが干渉しないようにする。
_CACHE_NEARBY_PENDING = "theater_nearby_pending"

# 劇場座標の永続キャッシュ（SQLite）のモジュールレベルシングルトン。
# テストでは app.routers.theaters.coord_cache を monkeypatch して差し替える。
coord_cache = CoordCache(settings.coord_cache_path)

# 詳細ページの住所抽出セレクタ（Filmarks 実HTML構造）
_ADDRESS_SELECTOR = "div.p-theater-movies-info__address"

# 座標補完処理中（in-flight）の theater_id 集合と、それを保護するロック。
# 未解決座標の重複補完（詳細ページ再取得・再ジオコーディング）を防ぐ。
_in_flight_lock = threading.Lock()
_in_flight: set[str] = set()

# 未解決座標が残る場合の近隣検索キャッシュTTL（秒）。
# 補完完了までの短期間キャッシュで /pia_theaters の再取得を抑止しつつ、
# 補完完了後は正規キャッシュ（cache_ttl_schedule）へ自然に移行させる。
_NEARBY_PENDING_TTL = 30.0

# バックグラウンド座標補完の開始前遅延（秒）。
# メインの近隣検索直後に補完を開始すると、プロセス共有の
# _throttle_lock/_last_request_at を奪い合って直後の API が不要にブロックする。
# テストでは conftest が 0.0 に差し替えて実行を高速化する。
_BACKGROUND_RESOLUTION_DELAY = 5.0


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

    - 引数の ``theaters`` は補完専用のオブジェクト（呼び出し側でレスポンス用
      オブジェクトから ``model_copy()`` で分離済み）。ここでミューテートしても
      レスポンスには影響しない。
    - 既に補完処理中（``_in_flight`` に存在）の theater はスキップし、重複補完を防ぐ。
    - 詳細ページ取得（get_html_batch）とジオコーディングは FilmarksClient を
      新規生成して実行する（リクエスト処理と分離し、5秒スロットルは引き続き守られる）。
    - 補完結果は SQLite（coord_cache）に保存されるため、次回リクエストで反映される。
    - 失敗しても例外を握りつぶし、メインのレスポンスには影響させない。
    - 補完対象が無ければスレッドを起動しない。
    """
    # in-flight の theater を除外し、新規補完対象のみをスレッドに回す。
    to_resolve: list[TheaterSummary] = []
    with _in_flight_lock:
        for t in theaters:
            if t.id in _in_flight:
                continue
            _in_flight.add(t.id)
            to_resolve.append(t)

    if not to_resolve:
        return

    def _task() -> None:
        try:
            # メインリクエストとのスロットル競合を避けるため遅延実行する。
            # 直後にバックグラウンド補完が始まると、プロセス共有の
            # `_throttle_lock/_last_request_at` をメインの近隣検索と奪い合い、
            # 補完完了時に `_last_request_at` を上書きして直後の API が
            # 不要に 5 秒ブロックする。ここで少し待つことで競合を緩和する。
            # 遅延 0 の場合は time.sleep(0) の GIL 解放によるタイミング変化を
            # 避けるため sleep 自体を呼ばない。
            if _BACKGROUND_RESOLUTION_DELAY > 0:
                time.sleep(_BACKGROUND_RESOLUTION_DELAY)
            with FilmarksClient() as client:
                _resolve_coords(client, to_resolve)
        except Exception:
            logger.warning("バックグラウンド座標補完に失敗しました", exc_info=True)
        finally:
            # 補完完了（成功・失敗を問わず）で in-flight から削除する。
            with _in_flight_lock:
                for t in to_resolve:
                    _in_flight.discard(t.id)

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
    # 正規キャッシュ（1時間）を先に確認し、無ければ短TTL（座標未解決中）の
    # キャッシュも確認する。短TTLは別名前空間のため、正規キャッシュと互いに
    # フラッシュし合うことはない（C1）。
    cached = cache_manager.get(_CACHE_NEARBY, key)
    if cached is None:
        cached = cache_manager.get(_CACHE_NEARBY_PENDING, key)
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
        # L5: Filmarks 側が想定外の JSON（list やスカラー）を返しても
        # AttributeError にならないよう dict に正規化する。
        if not isinstance(data, dict):
            data = {}
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
        # 未補完の劇場がある場合はバックグラウンドで補完する。レスポンス用
        # オブジェクト（result.theaters）と補完用オブジェクトを model_copy()
        # で分離し、メインスレッドのシリアライズ中に latitude のみセット・
        # longitude が None の途中状態が混入するのを防ぐ（M2）。
        _schedule_coord_resolution([t.model_copy() for t in pending])
        # 座標解決済みの劇場が1件でもあれば、短い TTL（30秒）でキャッシュして
        # 補完完了までの間の /pia_theaters 再取得を抑止する（M6）。
        # 短TTLは別名前空間（_CACHE_NEARBY_PENDING）を使う。同一名前空間で TTL が
        # 変わると TTLCache が作り直されて正規キャッシュもフラッシュされるため（C1）。
        if len(result.theaters) > len(pending):
            cache_manager.set(_CACHE_NEARBY_PENDING, key, result, _NEARBY_PENDING_TTL)
    else:
        # 全劇場の座標が揃っている場合のみ正規キャッシュ（1時間）する
        cache_manager.set(_CACHE_NEARBY, key, result, settings.cache_ttl_schedule)
    return result


# L6: /nearby は /{prefecture} より先に登録する必要がある。
# 型パラメータを持つ /{prefecture} を先に登録すると "/nearby" が
# prefecture と解釈されるパス衝突が起きるため、ルート定義順が重要。
@router.get("/nearby", response_model=NearbyResponse)
def nearby(
    lat: float = Query(..., ge=-90, le=90, description="現在地の緯度"),
    lng: float = Query(..., ge=-180, le=180, description="現在地の経度"),
    radius: float = Query(10.0, ge=1, le=100, description="検索半径（km）"),
) -> NearbyResponse:
    """近隣劇場検索。半径1〜100km。"""
    return _nearby(lat, lng, radius)


@router.get("/{prefecture}", response_model=AreaListResponse)
def get_prefecture(prefecture: str = Path(..., pattern=_PREFECTURE_PATTERN)) -> AreaListResponse:
    """都道府県別のエリア一覧。"""
    return _prefecture_list(prefecture)


@router.get(
    "/{prefecture}/{area_id}",
    response_model=TheaterListResponse,
)
def get_area(
    prefecture: str = Path(..., pattern=_PREFECTURE_PATTERN),
    area_id: str = Path(..., pattern=r"^\d+$"),
) -> TheaterListResponse:
    """エリア別の劇場一覧。"""
    return _area_list(prefecture, area_id)


@router.get(
    "/{prefecture}/{area_id}/{theater_id}",
    response_model=TheaterDetail,
)
def get_theater(
    prefecture: str = Path(..., pattern=_PREFECTURE_PATTERN),
    area_id: str = Path(..., pattern=r"^\d+$"),
    theater_id: str = Path(..., pattern=r"^\d+$"),
) -> TheaterDetail:
    """劇場詳細＋上映スケジュール。"""
    url_path = f"/theaters/{prefecture}/{area_id}/{theater_id}"
    return _theater_detail(url_path, prefecture, area_id, theater_id)