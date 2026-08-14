package com.filmy.app.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.AppContainer
import com.filmy.app.data.api.ApiClient
import com.filmy.app.data.api.dto.NearbyResponseDto
import com.filmy.app.data.repository.TheaterRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class NearbyViewModel : ViewModel() {

    private val repository = TheaterRepository(ApiClient.apiService)
    private val settingsDataStore = AppContainer.settingsDataStore

    private val _uiState = MutableStateFlow<UiState<NearbyResponseDto>>(UiState.Loading)
    val uiState: StateFlow<UiState<NearbyResponseDto>> = _uiState.asStateFlow()

    /** バックグラウンドで自動リフレッシュ中であることを表すフラグ。 */
    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    /** リフレッシュ時に再利用する直前の検索条件。 */
    private var lastLat: Double? = null
    private var lastLng: Double? = null

    /**
     * 現在の検索半径（km）。DataStore の変更を購読して常に最新値を保持する。
     * 設定画面で半径を変更すると、次回の loadNearby / refresh から新しい値が使われる。
     */
    private var currentRadiusKm: Double = DEFAULT_RADIUS_KM

    init {
        viewModelScope.launch {
            settingsDataStore.nearbyRadiusKm.collect { radius ->
                currentRadiusKm = radius.toDouble()
            }
        }
    }

    fun loadNearby(lat: Double, lng: Double) {
        lastLat = lat
        lastLng = lng
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val response = repository.getNearby(lat, lng, currentRadiusKm)
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
                val response = repository.getNearby(lat, lng, currentRadiusKm)
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
        const val DEFAULT_RADIUS_KM = 10.0
    }
}
