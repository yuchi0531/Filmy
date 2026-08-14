package com.filmy.app.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * お気に入り登録された劇場を永続化するエンティティ。
 */
@Entity(tableName = "favorite_theaters")
data class FavoriteTheaterEntity(
    @PrimaryKey val theaterId: String,
    val name: String,
    val address: String? = null,
    val prefecture: String? = null,
    val areaId: String? = null,
    val url: String? = null,
    val addedAt: Long = System.currentTimeMillis(),
)