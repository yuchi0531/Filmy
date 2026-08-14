package com.filmy.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.filmy.app.data.AppContainer
import com.filmy.app.data.local.FavoriteMovieEntity
import com.filmy.app.data.local.FavoriteTheaterEntity
import com.filmy.app.data.repository.BackupSerializer
import com.filmy.app.data.repository.FavoriteRepository
import com.filmy.app.data.repository.toBackupMovie
import com.filmy.app.data.repository.toBackupTheater
import com.filmy.app.data.repository.toEntity
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * 設定画面の ViewModel。
 * 近隣検索半径（DataStore）と、お気に入りのエクスポート/インポートを担う。
 */
class SettingsViewModel : ViewModel() {

    private val settingsDataStore = AppContainer.settingsDataStore
    private val favoriteRepository: FavoriteRepository = AppContainer.favoriteRepository

    /** 近隣検索の半径（km）。DataStore を購読し、変更をリアルタイムに反映する。 */
    val nearbyRadiusKm: StateFlow<Float> = settingsDataStore.nearbyRadiusKm
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), 10.0f)

    fun setNearbyRadiusKm(radius: Float) {
        viewModelScope.launch {
            settingsDataStore.setNearbyRadiusKm(radius)
        }
    }

    /**
     * お気に入り（映画・劇場）をバックアップ JSON として直列化する。
     * 実際のファイル書き込みは呼び出し側（SAF の outputStream）で行う。
     */
    suspend fun exportFavorites(): String {
        val movies = favoriteRepository.getAllFavoriteMovies().map { it.toBackupMovie() }
        val theaters = favoriteRepository.getAllFavoriteTheaters().map { it.toBackupTheater() }
        return BackupSerializer.serialize(movies, theaters)
    }

    /**
     * バックアップ JSON を復元する。
     * 既存のお気に入りは保持しつつ、同一IDは REPLACE で上書きする。
     */
    suspend fun importFavorites(json: String) {
        val backup = BackupSerializer.deserialize(json)
        val movies: List<FavoriteMovieEntity> = backup.movies.map { it.toEntity() }
        val theaters: List<FavoriteTheaterEntity> = backup.theaters.map { it.toEntity() }
        favoriteRepository.importMovies(movies)
        favoriteRepository.importTheaters(theaters)
    }
}
