package com.filmy.app.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.api.dto.MovieListResponseDto
import com.filmy.app.data.api.dto.MovieSummaryDto
import com.filmy.app.data.repository.MovieRepository
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.supervisorScope

/** Home 画面に表示する各カテゴリの映画リスト。 */
data class HomeUiData(
    val now: List<MovieSummaryDto> = emptyList(),
    val coming: List<MovieSummaryDto> = emptyList(),
    val trend: List<MovieSummaryDto> = emptyList(),
)

class HomeViewModel : ViewModel() {

    private val repository = MovieRepository()

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
        // L6: フラグのセットをコルーチン起動前（同期的）に原子的に行い、
        // check-then-act の競合による二重フェッチを防ぐ。
        if (!_isRefreshing.compareAndSet(false, true)) return
        viewModelScope.launch {
            try {
                _uiState.value = UiState.Success(fetch())
            } catch (e: Exception) {
                Log.w(TAG, "refresh failed", e)
            } finally {
                _isRefreshing.value = false
            }
        }
    }

    private suspend fun fetch(): HomeUiData = supervisorScope {
        // 各カテゴリは独立に失敗を吸収し、1 件の失敗で他 2 件の成功データを破棄しない。
        val now = async { runCatching { repository.getNowPlaying() }.getOrElse { Log.w(TAG, "now failed", it); MovieListResponseDto() } }
        val coming = async { runCatching { repository.getComingSoon() }.getOrElse { Log.w(TAG, "coming failed", it); MovieListResponseDto() } }
        val trend = async { runCatching { repository.getTrending() }.getOrElse { Log.w(TAG, "trend failed", it); MovieListResponseDto() } }
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