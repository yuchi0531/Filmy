package com.filmy.app.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

/**
 * お気に入りを永続化する Room Database。
 * シングルトンとして [getInstance] から取得する。
 *
 * Schema エクスポート方針:
 * - [exportSchema] = true でビルド時に `app/schemas` へ JSON を出力する。
 * - 将来のマイグレーション（version アップ時）でスキーマ差分を検証できるようにするため。
 * - 設定場所は app/build.gradle.kts の `ksp { arg("room.schemaLocation", ...) }`。
 */
@Database(
    entities = [FavoriteMovieEntity::class, FavoriteTheaterEntity::class],
    version = 1,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {

    abstract fun favoriteMovieDao(): FavoriteMovieDao

    abstract fun favoriteTheaterDao(): FavoriteTheaterDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase =
            INSTANCE ?: synchronized(this) {
                INSTANCE ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "filmy.db",
                ).build().also { INSTANCE = it }
            }
    }
}