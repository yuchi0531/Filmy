package com.filmy.app.data.api.dto

/**
 * 都道府県ページのエリア一覧用サマリー。
 * バックエンドの AreaSummary モデルに対応。
 */
data class AreaSummaryDto(
    val id: String,
    val name: String,
    val theater_count: Int? = null,
    val url: String? = null,
)

/**
 * 都道府県ページ（エリア一覧）のレスポンス。
 * バックエンドの AreaListResponse モデルに対応。
 */
data class AreaListResponseDto(
    val prefecture: String? = null,
    val results: List<AreaSummaryDto> = emptyList(),
    val total: Int = 0,
)