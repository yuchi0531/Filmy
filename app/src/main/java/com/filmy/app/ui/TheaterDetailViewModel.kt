package com.filmy.app.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.AppContainer
import com.filmy.app.data.api.ApiClient
import com.filmy.app.data.api.dto.TheaterDetailDto
import com.filmy.app.data.repository.FavoriteRepository
import com.filmy.app.data.repository.TheaterRepository
import com.filmy.app.data.repository.toFavoriteEntity
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 劇場詳細画面の ViewModel。
 * [loadTheaterDetail] で `/api/theaters/{prefecture}/{area_id}/{theater_id}` を取得する。
 */
class TheaterDetailViewModel : ViewModel() {

    private val repository = TheaterRepository(ApiClient.apiService)

    private val favoriteRepository = AppContainer.favoriteRepository

    private val _uiState = MutableStateFlow<UiState<TheaterDetailDto>>(UiState.Loading)
    val uiState: StateFlow<UiState<TheaterDetailDto>> = _uiState.asStateFlow()

    /** 再試行時に再利用する直前の検索条件。 */
    private var lastPrefecture: String? = null
    private var lastAreaId: String? = null
    private var lastTheaterId: String? = null

    fun loadTheaterDetail(prefecture: String, areaId: String, theaterId: String) {
        lastPrefecture = prefecture
        lastAreaId = areaId
        lastTheaterId = theaterId
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val detail = repository.getTheaterDetail(prefecture, areaId, theaterId)
                _uiState.value = UiState.Success(detail)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Log.w(TAG, "loadTheaterDetail failed", e)
                _uiState.value = UiState.Error(e.message ?: "劇場情報を取得できませんでした")
            }
        }
    }

    /** 最後に指定された条件で再取得する（エラーからの再試行用）。 */
    fun retry() {
        val prefecture = lastPrefecture ?: return
        val areaId = lastAreaId ?: return
        val theaterId = lastTheaterId ?: return
        loadTheaterDetail(prefecture, areaId, theaterId)
    }

    /** お気に入り状態をリアルタイムに反映する Flow。 */
    fun isFavorite(theaterId: String): Flow<Boolean> =
        favoriteRepository.isTheaterFavorite(theaterId)

    /** お気に入り登録/解除を切り替える。prefecture / areaId は詳細画面遷移時の値（DTO に無い場合のフォールバック）。 */
    fun toggleFavorite(theater: TheaterDetailDto, prefecture: String, areaId: String) {
        viewModelScope.launch {
            favoriteRepository.toggleTheaterFavorite(
                theater.toFavoriteEntity(prefectureFallback = prefecture, areaIdFallback = areaId)
            )
        }
    }

    private companion object {
        const val TAG = "TheaterDetailViewModel"
    }
}
