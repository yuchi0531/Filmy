package com.filmy.app.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.api.ApiClient
import com.filmy.app.data.api.dto.NearbyResponseDto
import com.filmy.app.data.repository.TheaterRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class NearbyViewModel : ViewModel() {

    private val repository = TheaterRepository(ApiClient.apiService)

    private val _uiState = MutableStateFlow<UiState<NearbyResponseDto>>(UiState.Loading)
    val uiState: StateFlow<UiState<NearbyResponseDto>> = _uiState.asStateFlow()

    /** バックグラウンドで自動リフレッシュ中であることを表すフラグ。 */
    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    /** リフレッシュ時に再利用する直前の検索条件。 */
    private var lastLat: Double? = null
    private var lastLng: Double? = null
    private var lastRadiusKm: Double = 10.0

    fun loadNearby(lat: Double, lng: Double, radiusKm: Double = 10.0) {
        lastLat = lat
        lastLng = lng
        lastRadiusKm = radiusKm
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = repository.getNearby(lat, lng, radiusKm)
                _uiState.value = UiState.Success(response)
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "近隣の劇場情報を取得できませんでした")
            }
        }
    }

    /**
     * 既存データを Loading 状態に戻さずに、最後に取得した座標で再取得する（30秒自動リフレッシュ用）。
     * まだ一度も取得していない、またはリフレッシュ中の場合は何もしない。
     * 失敗した場合は現在の表示を保持する。
     */
    fun refresh() {
        val lat = lastLat ?: return
        val lng = lastLng ?: return
        if (_isRefreshing.value) return
        viewModelScope.launch {
            _isRefreshing.value = true
            try {
                val response = repository.getNearby(lat, lng, lastRadiusKm)
                _uiState.value = UiState.Success(response)
            } catch (e: Exception) {
                Log.w(TAG, "refresh failed", e)
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    private companion object {
        const val TAG = "NearbyViewModel"
    }
}