package com.filmy.app.ui

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.AppContainer
import com.filmy.app.data.api.dto.MovieDetailDto
import com.filmy.app.data.repository.FavoriteRepository
import com.filmy.app.data.repository.MovieRepository
import com.filmy.app.data.repository.toFavoriteEntity
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 映画詳細画面の ViewModel。
 * [loadMovieDetail] で `/api/movies/{movie_id}` を取得する。
 */
class MovieDetailViewModel : ViewModel() {

    private val repository = MovieRepository()

    private val favoriteRepository = AppContainer.favoriteRepository

    private val _uiState = MutableStateFlow<UiState<MovieDetailDto>>(UiState.Loading)
    val uiState: StateFlow<UiState<MovieDetailDto>> = _uiState.asStateFlow()

    /** 再試行時に再利用する直前の映画 ID。 */
    private var lastMovieId: String? = null

    fun loadMovieDetail(movieId: String) {
        lastMovieId = movieId
        _uiState.value = UiState.Loading
        viewModelScope.launch {
            try {
                val detail = repository.getDetail(movieId)
                _uiState.value = UiState.Success(detail)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                Log.w(TAG, "loadMovieDetail failed", e)
                _uiState.value = UiState.Error(e.message ?: "映画情報を取得できませんでした")
            }
        }
    }

    /** 最後に指定された映画を再取得する（エラーからの再試行用）。 */
    fun retry() {
        val movieId = lastMovieId ?: return
        loadMovieDetail(movieId)
    }

    /** お気に入り状態をリアルタイムに反映する Flow。 */
    fun isFavorite(movieId: String): Flow<Boolean> =
        favoriteRepository.isMovieFavorite(movieId)

    /** お気に入り登録/解除を切り替える。 */
    fun toggleFavorite(movie: MovieDetailDto) {
        viewModelScope.launch {
            favoriteRepository.toggleMovieFavorite(movie.toFavoriteEntity())
        }
    }

    private companion object {
        const val TAG = "MovieDetailViewModel"
    }
}
