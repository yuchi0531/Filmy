package com.filmy.app.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

/**
 * お気に入り映画の CRUD を行う DAO。
 */
@Dao
interface FavoriteMovieDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(movie: FavoriteMovieEntity)

    /** バックアップ復元用。既存は保持しつつ、同一IDは REPLACE で上書きする。 */
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(movies: List<FavoriteMovieEntity>)

    @Delete
    suspend fun delete(movie: FavoriteMovieEntity)

    @Query("SELECT * FROM favorite_movies ORDER BY addedAt DESC")
    fun observeAll(): Flow<List<FavoriteMovieEntity>>

    /** バックアップエクスポート用に全件取得する。 */
    @Query("SELECT * FROM favorite_movies ORDER BY addedAt DESC")
    suspend fun getAll(): List<FavoriteMovieEntity>

    @Query("SELECT * FROM favorite_movies WHERE movieId = :id")
    fun observeById(id: String): Flow<FavoriteMovieEntity?>

    @Query("SELECT EXISTS(SELECT 1 FROM favorite_movies WHERE movieId = :id)")
    suspend fun isFavorite(id: String): Boolean

    /** 登録済みなら解除、未登録なら追加を単一トランザクションで行う（check-then-act の TOCTOU を防ぐ）。 */
    @Transaction
    suspend fun toggle(movie: FavoriteMovieEntity) {
        if (isFavorite(movie.movieId)) {
            delete(movie)
        } else {
            insert(movie)
        }
    }
}