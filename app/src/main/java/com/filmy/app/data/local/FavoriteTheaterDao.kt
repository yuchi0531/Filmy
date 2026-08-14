package com.filmy.app.data.local

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow

/**
 * お気に入り劇場の CRUD を行う DAO。
 */
@Dao
interface FavoriteTheaterDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(theater: FavoriteTheaterEntity)

    @Delete
    suspend fun delete(theater: FavoriteTheaterEntity)

    @Query("SELECT * FROM favorite_theaters ORDER BY addedAt DESC")
    fun observeAll(): Flow<List<FavoriteTheaterEntity>>

    @Query("SELECT * FROM favorite_theaters WHERE theaterId = :id")
    fun observeById(id: String): Flow<FavoriteTheaterEntity?>

    @Query("SELECT EXISTS(SELECT 1 FROM favorite_theaters WHERE theaterId = :id)")
    suspend fun isFavorite(id: String): Boolean

    /** 登録済みなら解除、未登録なら追加を単一トランザクションで行う（check-then-act の TOCTOU を防ぐ）。 */
    @Transaction
    suspend fun toggle(theater: FavoriteTheaterEntity) {
        if (isFavorite(theater.theaterId)) {
            delete(theater)
        } else {
            insert(theater)
        }
    }
}