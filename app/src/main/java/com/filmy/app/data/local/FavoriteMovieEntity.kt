package com.filmy.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * お気に入り登録された映画を永続化するエンティティ。
 */
@Entity(tableName = "favorite_movies")
data class FavoriteMovieEntity(
    @PrimaryKey val movieId: String,
    val title: String,
    val posterUrl: String? = null,
    val rating: Double? = null,
    val releaseDate: String? = null,
    val addedAt: Long = System.currentTimeMillis(),
)