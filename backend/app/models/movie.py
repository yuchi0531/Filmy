"""映画関連の Pydantic モデル。"""

from pydantic import BaseModel, Field


class CastMember(BaseModel):
    """出演者。character は役名（無い場合は None）。"""

    name: str
    character: str | None = None


class StreamingInfo(BaseModel):
    """配信情報。type は「見放題/レンタル/購入」等。"""

    service: str
    type: str  # 見放題/レンタル/購入


class MovieSummary(BaseModel):
    """映画の一覧用サマリー。"""

    id: str
    title: str
    original_title: str | None = None
    rating: float | None = None
    review_count: int | None = None
    poster_url: str | None = None
    release_date: str | None = None
    genres: list[str] = Field(default_factory=list)
    mark_count: int | None = None
    clip_count: int | None = None


class MovieDetail(MovieSummary):
    """映画の詳細。MovieSummary を継承する。"""

    synopsis: str | None = None
    runtime: str | None = None
    director: list[str] = Field(default_factory=list)
    cast: list[CastMember] = Field(default_factory=list)
    official_site: str | None = None
    streaming: list[StreamingInfo] = Field(default_factory=list)


class MovieListResponse(BaseModel):
    """映画一覧（上映中・公開予定・検索結果など）のレスポンス。"""

    query: str | None = None
    heading: str | None = None
    results: list[MovieSummary]
    total: int
    page: int = 1
    has_next: bool = False