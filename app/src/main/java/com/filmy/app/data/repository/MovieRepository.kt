package com.filmy.app.data.repository

import com.filmy.app.data.api.FilmyApiService
import com.filmy.app.data.api.dto.MovieDetailDto
import com.filmy.app.data.api.dto.MovieListResponseDto

/**
 * 映画関連のデータ取得をまとめる Repository。
 */
class MovieRepository(private val apiService: FilmyApiService) {

    suspend fun getNowPlaying(page: Int = 1): MovieListResponseDto =
        apiService.getNowPlayingMovies(page)

    suspend fun getComingSoon(page: Int = 1): MovieListResponseDto =
        apiService.getComingSoonMovies(page)

    suspend fun getUpcoming(page: Int = 1): MovieListResponseDto =
        apiService.getUpcomingMovies(page)

    suspend fun getTrending(page: Int = 1): MovieListResponseDto =
        apiService.getTrendingMovies(page)

    suspend fun getDetail(movieId: String): MovieDetailDto =
        apiService.getMovieDetail(movieId)

    suspend fun search(query: String, page: Int = 1): MovieListResponseDto =
        apiService.searchMovies(query, page)
}
