package com.filmy.app.data.repository

import com.filmy.app.data.api.dto.MovieDetailDto
import com.filmy.app.data.api.dto.TheaterDetailDto
import com.filmy.app.data.local.FavoriteMovieDao
import com.filmy.app.data.local.FavoriteMovieEntity
import com.filmy.app.data.local.FavoriteTheaterDao
import com.filmy.app.data.local.FavoriteTheaterEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/**
 * お気に入り登録/解除・一覧取得をまとめる Repository。
 * 登録済みなら解除、未登録なら追加するトグル操作を提供する。
 */
class FavoriteRepository(
    private val movieDao: FavoriteMovieDao,
    private val theaterDao: FavoriteTheaterDao,
) {

    /** 登録済みなら解除、未登録なら追加する。check + act は DAO 側の [FavoriteMovieDao.toggle] で原子的に実行する。 */
    suspend fun toggleMovieFavorite(movie: FavoriteMovieEntity) {
        movieDao.toggle(movie)
    }

    /** 登録済みなら解除、未登録なら追加する。check + act は DAO 側の [FavoriteTheaterDao.toggle] で原子的に実行する。 */
    suspend fun toggleTheaterFavorite(theater: FavoriteTheaterEntity) {
        theaterDao.toggle(theater)
    }

    fun observeFavoriteMovies(): Flow<List<FavoriteMovieEntity>> = movieDao.observeAll()

    fun observeFavoriteTheaters(): Flow<List<FavoriteTheaterEntity>> = theaterDao.observeAll()

    /** 登録状態をリアルタイムに反映する Flow。 */
    fun isMovieFavorite(id: String): Flow<Boolean> = movieDao.observeById(id).map { it != null }

    /** 登録状態をリアルタイムに反映する Flow。 */
    fun isTheaterFavorite(id: String): Flow<Boolean> = theaterDao.observeById(id).map { it != null }
}

/** 詳細DTOを保存用エンティティに変換する。 */
fun MovieDetailDto.toFavoriteEntity(): FavoriteMovieEntity = FavoriteMovieEntity(
    movieId = id,
    title = title,
    posterUrl = poster_url,
    rating = rating,
    releaseDate = release_date,
)

/**
 * 詳細DTOを保存用エンティティに変換する。
 * DTO に prefecture / area_id が無い場合は、詳細画面遷移時に使われた値（[prefectureFallback] / [areaIdFallback]）を
 * フォールバックとして保存し、お気に入りからの遷移で空のルート引数にならないようにする。
 */
fun TheaterDetailDto.toFavoriteEntity(
    prefectureFallback: String? = null,
    areaIdFallback: String? = null,
): FavoriteTheaterEntity = FavoriteTheaterEntity(
    theaterId = id,
    name = name,
    address = address,
    prefecture = prefecture ?: prefectureFallback,
    areaId = area_id ?: areaIdFallback,
    url = url,
)