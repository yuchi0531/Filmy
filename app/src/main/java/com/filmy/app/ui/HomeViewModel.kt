package com.filmy.app.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.api.ApiClient
import com.filmy.app.data.api.dto.MovieSummaryDto
import com.filmy.app.data.repository.MovieRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Home 画面に表示する各カテゴリの映画リスト。 */
data class HomeUiData(
    val now: List<MovieSummaryDto> = emptyList(),
    val coming: List<MovieSummaryDto> = emptyList(),
    val trend: List<MovieSummaryDto> = emptyList(),
)

class HomeViewModel : ViewModel() {

    private val repository = MovieRepository(ApiClient.apiService)

    private val _uiState = MutableStateFlow<UiState<HomeUiData>>(UiState.Loading)
    val uiState: StateFlow<UiState<HomeUiData>> = _uiState.asStateFlow()

    /** バックグラウンドで自動リフレッシュ中であることを表すフラグ。 */
    private val _isRefreshing = MutableStateFlow(false)
    val isRefreshing: StateFlow<Boolean> = _isRefreshing.asStateFlow()

    init {
        load()
    }

    fun load() {
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            try {
                _uiState.value = UiState.Success(fetch())
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "映画情報を取得できませんでした")
            }
        }
    }

    /**
     * 既存データを Loading 状態に戻さずに再取得する（30秒自動リフレッシュ用）。
     * 失敗した場合は現在の表示を保持する。
     */
    fun refresh() {
        if (_isRefreshing.value) return
        viewModelScope.launch {
            _isRefreshing.value = true
            try {
                _uiState.value = UiState.Success(fetch())
            } catch (e: Exception) {
                Log.w(TAG, "refresh failed", e)
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    private suspend fun fetch(): HomeUiData = coroutineScope {
        val now = async { repository.getNowPlaying() }
        val coming = async { repository.getComingSoon() }
        val trend = async { repository.getTrending() }
        HomeUiData(
            now = now.await().results,
            coming = coming.await().results,
            trend = trend.await().results,
        )
    }

    private companion object {
        const val TAG = "HomeViewModel"
    }
}