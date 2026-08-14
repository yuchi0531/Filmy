package com.filmy.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.AppContainer
import com.filmy.app.data.local.FavoriteMovieEntity
import com.filmy.app.data.local.FavoriteTheaterEntity
import com.filmy.app.data.repository.FavoriteRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn

/**
 * お気に入り一覧画面の ViewModel。
 * Room の Flow を StateFlow に変換して画面へ公開する。
 */
class FavoritesViewModel : ViewModel() {

    private val favoriteRepository = AppContainer.favoriteRepository

    val favoriteMovies: StateFlow<List<FavoriteMovieEntity>> =
        favoriteRepository.observeFavoriteMovies()
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())

    val favoriteTheaters: StateFlow<List<FavoriteTheaterEntity>> =
        favoriteRepository.observeFavoriteTheaters()
            .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
}