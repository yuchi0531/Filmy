package com.filmy.app.data.api.dto

/**
 * 近隣劇場検索のレスポンス。
 * バックエンドの NearbyResponse モデルに対応。
 */
data class NearbyResponseDto(
    val latitude: Double = 0.0,
    val longitude: Double = 0.0,
    val radius_km: Double = 0.0,
    val theaters: List<TheaterSummaryDto> = emptyList(),
)