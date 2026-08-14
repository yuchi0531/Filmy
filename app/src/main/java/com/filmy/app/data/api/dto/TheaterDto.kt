package com.filmy.app.data.api.dto

/**
 * 劇場の一覧用サマリー。
 * バックエンドの TheaterSummary モデルに対応。
 */
data class TheaterSummaryDto(
    val id: String,
    val name: String,
    val address: String? = null,
    val prefecture: String? = null,
    val area_id: String? = null,
    val url: String? = null,
    val distance_km: Double? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
)

/**
 * 劇場の詳細（スケジュール含む）。
 * バックエンドの TheaterDetail モデルに対応。
 */
data class TheaterDetailDto(
    val id: String,
    val name: String,
    val address: String? = null,
    val prefecture: String? = null,
    val area_id: String? = null,
    val url: String? = null,
    val distance_km: Double? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val map_url: String? = null,
    val movies: List<MovieScheduleDto> = emptyList(),
)

/**
 * 劇場の上映スケジュール（映画単位）。
 * dates は {"2026-08-14": ["10:00", "13:00"]} の形式（日付 → 上映時刻リスト）。
 */
data class MovieScheduleDto(
    val movie_id: String,
    val movie_title: String,
    val poster_url: String? = null,
    val dates: Map<String, List<String>> = emptyMap(),
)

/**
 * 劇場一覧（エリア別）のレスポンス。
 * バックエンドの TheaterListResponse モデルに対応。
 */
data class TheaterListResponseDto(
    val prefecture: String? = null,
    val results: List<TheaterSummaryDto> = emptyList(),
    val total: Int = 0,
)