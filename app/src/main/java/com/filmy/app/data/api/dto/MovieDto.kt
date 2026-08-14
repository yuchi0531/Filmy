package com.filmy.app.data.api.dto

/**
 * 映画の一覧用サマリー。
 * バックエンドの MovieSummary モデルに対応。
 */
data class MovieSummaryDto(
    val id: String,
    val title: String,
    val original_title: String? = null,
    val rating: Double? = null,
    val review_count: Int? = null,
    val poster_url: String? = null,
    val release_date: String? = null,
    val genres: List<String> = emptyList(),
    val mark_count: Int? = null,
    val clip_count: Int? = null,
)

/**
 * 映画の詳細。MovieSummary の全フィールドに加えて詳細情報を持つ。
 * バックエンドの MovieDetail モデルに対応。
 */
data class MovieDetailDto(
    val id: String,
    val title: String,
    val original_title: String? = null,
    val rating: Double? = null,
    val review_count: Int? = null,
    val poster_url: String? = null,
    val release_date: String? = null,
    val genres: List<String> = emptyList(),
    val mark_count: Int? = null,
    val clip_count: Int? = null,
    val synopsis: String? = null,
    val runtime: String? = null,
    val director: List<String> = emptyList(),
    val cast: List<CastMember> = emptyList(),
    val official_site: String? = null,
    val streaming: List<StreamingInfo> = emptyList(),
)

/** 出演者。character は役名（無い場合は null）。 */
data class CastMember(
    val name: String,
    val character: String? = null,
)

/** 配信情報。type は「見放題/レンタル/購入」等。 */
data class StreamingInfo(
    val service: String,
    val type: String,
)

/**
 * 映画一覧（上映中・公開予定・検索結果など）のレスポンス。
 * バックエンドの MovieListResponse モデルに対応。
 */
data class MovieListResponseDto(
    val query: String? = null,
    val heading: String? = null,
    val results: List<MovieSummaryDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    val has_next: Boolean = false,
)
