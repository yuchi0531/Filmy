package com.filmy.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.api.dto.MovieListResponseDto
import com.filmy.app.data.repository.MovieRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.coroutines.cancellation.CancellationException

class SearchViewModel : ViewModel() {

    private val repository = MovieRepository()

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    private val _uiState = MutableStateFlow<UiState<MovieListResponseDto>>(UiState.Loading)
    val uiState: StateFlow<UiState<MovieListResponseDto>> = _uiState.asStateFlow()

    /** 実行中の検索ジョブ。既存の検索をキャンセルして競合を防ぐ。 */
    private var searchJob: Job? = null

    fun onQueryChange(value: String) {
        _query.value = value
    }

    fun search() {
        val q = _query.value.trim()
        if (q.isEmpty()) return
        // 前回の検索がまだ応答を返していない場合、古いレスポンスで結果が上書きされないよう先にキャンセルする。
        searchJob?.cancel()
        _uiState.value = UiState.Loading
        searchJob = viewModelScope.launch {
            try {
                val response = repository.search(q)
                _uiState.value = UiState.Success(response)
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _uiState.value = UiState.Error(e.message ?: "検索できませんでした")
            }
        }
    }
}