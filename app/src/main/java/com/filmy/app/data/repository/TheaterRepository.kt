package com.filmy.app.data.repository

import com.filmy.app.data.api.ApiClient
import com.filmy.app.data.api.FilmyApiService
import com.filmy.app.data.api.dto.AreaListResponseDto
import com.filmy.app.data.api.dto.NearbyResponseDto
import com.filmy.app.data.api.dto.TheaterDetailDto
import com.filmy.app.data.api.dto.TheaterListResponseDto

/**
 * 劇場関連のデータ取得をまとめる Repository。
 * ベース URL は [ApiClient] が保持し、URL 変更後は次の呼び出しから新 URL が使われる。
 */
class TheaterRepository {

    private val apiService: FilmyApiService get() = ApiClient.apiService

    suspend fun getAreas(prefecture: String): AreaListResponseDto =
        apiService.getAreas(prefecture)

    suspend fun getTheatersByArea(prefecture: String, areaId: String): TheaterListResponseDto =
        apiService.getTheatersByArea(prefecture, areaId)

    suspend fun getTheaterDetail(prefecture: String, areaId: String, theaterId: String): TheaterDetailDto =
        apiService.getTheaterDetail(prefecture, areaId, theaterId)

    suspend fun getNearby(lat: Double, lng: Double, radiusKm: Double = 10.0): NearbyResponseDto =
        apiService.getNearby(lat, lng, radiusKm)
}
