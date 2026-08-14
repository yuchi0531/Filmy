package com.filmy.app.data.api

import com.filmy.app.data.api.dto.*
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface FilmyApiService {
    // Movies
    @GET("api/movies/now")
    suspend fun getNowPlayingMovies(@Query("page") page: Int = 1): MovieListResponseDto

    @GET("api/movies/coming")
    suspend fun getComingSoonMovies(@Query("page") page: Int = 1): MovieListResponseDto

    @GET("api/movies/upcoming")
    suspend fun getUpcomingMovies(@Query("page") page: Int = 1): MovieListResponseDto

    @GET("api/movies/trend")
    suspend fun getTrendingMovies(@Query("page") page: Int = 1): MovieListResponseDto

    @GET("api/movies/{movie_id}")
    suspend fun getMovieDetail(@Path("movie_id") movieId: String): MovieDetailDto

    // Search
    @GET("api/search")
    suspend fun searchMovies(
        @Query("q") query: String,
        @Query("page") page: Int = 1,
    ): MovieListResponseDto

    // Theaters
    @GET("api/theaters/{prefecture}")
    suspend fun getAreas(@Path("prefecture") prefecture: String): AreaListResponseDto

    @GET("api/theaters/{prefecture}/{area_id}")
    suspend fun getTheatersByArea(
        @Path("prefecture") prefecture: String,
        @Path("area_id") areaId: String,
    ): TheaterListResponseDto

    @GET("api/theaters/{prefecture}/{area_id}/{theater_id}")
    suspend fun getTheaterDetail(
        @Path("prefecture") prefecture: String,
        @Path("area_id") areaId: String,
        @Path("theater_id") theaterId: String,
    ): TheaterDetailDto

    // Nearby
    @GET("api/theaters/nearby")
    suspend fun getNearby(
        @Query("lat") lat: Double,
        @Query("lng") lng: Double,
        @Query("radius") radius: Double = 10.0,
    ): NearbyResponseDto
}
