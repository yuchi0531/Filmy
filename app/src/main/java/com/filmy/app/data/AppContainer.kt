package com.filmy.app.data

import com.filmy.app.data.local.AppDatabase
import com.filmy.app.data.repository.FavoriteRepository

/**
 * アプリ全体で共有する依存の簡易コンテナ。
 * [AppDatabase] は [FilmyApplication] の onCreate で初期化される。
 * Repository は [database] の初期化後に初回アクセス時（by lazy）に生成される。
 */
object AppContainer {
    lateinit var database: AppDatabase

    /** 各 ViewModel から個別に生成するのを避け、ここで 1 つにまとめる。 */
    val favoriteRepository: FavoriteRepository by lazy {
        FavoriteRepository(
            movieDao = database.favoriteMovieDao(),
            theaterDao = database.favoriteTheaterDao(),
        )
    }
}