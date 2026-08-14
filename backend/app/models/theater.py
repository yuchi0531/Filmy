"""劇場関連の Pydantic モデル。"""

from pydantic import BaseModel, Field


class MovieSchedule(BaseModel):
    """劇場の上映スケジュール（映画単位）。

    ``dates`` は ``{"2026-08-14": ["10:00", "13:00"]}`` の形式（日付 → 上映時刻リスト）。
    """

    movie_id: str
    movie_title: str
    poster_url: str | None = None
    dates: dict[str, list[str]] = Field(default_factory=dict)


class TheaterSummary(BaseModel):
    """劇場の一覧用サマリー。"""

    id: str
    name: str
    address: str | None = None
    prefecture: str
    area_id: str | None = None
    url: str | None = None  # Filmarks の劇場URL（/theaters/{pref}/{area}/{id}）
    distance_km: float | None = None  # 近隣検索時のみ
    latitude: float | None = None  # 国土地理院APIで住所から解決（未解決なら None）
    longitude: float | None = None  # 同上


class TheaterDetail(TheaterSummary):
    """劇場の詳細（スケジュール含む）。TheaterSummary を継承する。

    ``latitude``/``longitude`` は TheaterSummary から継承する。
    """

    map_url: str | None = None
    movies: list[MovieSchedule] = Field(default_factory=list)


class AreaSummary(BaseModel):
    """都道府県ページのエリア一覧用サマリー。

    ``theater_count`` はエリア名に含まれる劇場数（例「新宿(4)」の 4）で、
    取得できた場合のみ設定される。
    """

    id: str
    name: str
    theater_count: int | None = None
    url: str | None = None


class TheaterListResponse(BaseModel):
    """劇場一覧（エリア別）のレスポンス。"""

    prefecture: str
    results: list[TheaterSummary]
    total: int


class AreaListResponse(BaseModel):
    """都道府県ページ（エリア一覧）のレスポンス。"""

    prefecture: str
    results: list[AreaSummary]
    total: int


class NearbyResponse(BaseModel):
    """近隣劇場検索のレスポンス。"""

    latitude: float
    longitude: float
    radius_km: float
    theaters: list[TheaterSummary]