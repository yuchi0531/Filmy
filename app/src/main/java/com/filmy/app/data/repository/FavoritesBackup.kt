package com.filmy.app.data.repository

import com.filmy.app.data.local.FavoriteMovieEntity
import com.filmy.app.data.local.FavoriteTheaterEntity
import com.google.gson.Gson

/**
 * お気に入りバックアップの JSON モデル。
 * Gson でシリアライズ/デシリアライズする。
 *
 * ```json
 * {
 *   "version": 1,
 *   "movies": [...],
 *   "theaters": [...]
 * }
 * ```
 */
data class FavoritesBackup(
    val version: Int = 1,
    val movies: List<BackupMovie> = emptyList(),
    val theaters: List<BackupTheater> = emptyList(),
)

/** バックアップ内の映画レコード。 */
data class BackupMovie(
    val movieId: String,
    val title: String,
    val posterUrl: String? = null,
    val rating: Double? = null,
    val releaseDate: String? = null,
    val addedAt: Long = 0L,
)

/** バックアップ内の劇場レコード。 */
data class BackupTheater(
    val theaterId: String,
    val name: String,
    val address: String? = null,
    val prefecture: String? = null,
    val areaId: String? = null,
    val url: String? = null,
    val addedAt: Long = 0L,
)

fun FavoriteMovieEntity.toBackupMovie(): BackupMovie = BackupMovie(
    movieId = movieId,
    title = title,
    posterUrl = posterUrl,
    rating = rating,
    releaseDate = releaseDate,
    addedAt = addedAt,
)

fun BackupMovie.toEntity(): FavoriteMovieEntity = FavoriteMovieEntity(
    movieId = movieId,
    title = title,
    posterUrl = posterUrl,
    rating = rating,
    releaseDate = releaseDate,
    addedAt = addedAt,
)

fun FavoriteTheaterEntity.toBackupTheater(): BackupTheater = BackupTheater(
    theaterId = theaterId,
    name = name,
    address = address,
    prefecture = prefecture,
    areaId = areaId,
    url = url,
    addedAt = addedAt,
)

fun BackupTheater.toEntity(): FavoriteTheaterEntity = FavoriteTheaterEntity(
    theaterId = theaterId,
    name = name,
    address = address,
    prefecture = prefecture,
    areaId = areaId,
    url = url,
    addedAt = addedAt,
)

/** Gson によるバックアップ JSON の直列化/復元を担う。 */
object BackupSerializer {
    private val gson = Gson()

    fun serialize(movies: List<BackupMovie>, theaters: List<BackupTheater>): String =
        gson.toJson(FavoritesBackup(version = 1, movies = movies, theaters = theaters))

    fun deserialize(json: String): FavoritesBackup {
        // L9: Gson はフィールドへ null を直接注入し得る（例: `null` や `{"movies": null}`）。
        // 非null型フィールドでも実行時には null になり得るため、トップレベルの null は
        // 空バックアップへ、movies/theaters の null は空リストへ正規化して NPE を防ぐ。
        val backup = gson.fromJson(json, FavoritesBackup::class.java)
            ?: return FavoritesBackup()
        return backup.copy(
            movies = backup.movies.orEmpty(),
            theaters = backup.theaters.orEmpty(),
        )
    }
}
