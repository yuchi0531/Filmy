package com.filmy.app.data.api

import com.filmy.app.BuildConfig
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.logging.HttpLoggingInterceptor
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * API クライアントのシングルトン。
 * ベース URL は [updateBaseUrl] で動的に変更でき、変更後は次回 [apiService] アクセス時に
 * Retrofit サービスが再生成される（設定画面からのサーバーURL変更を即時反映する）。
 */
object ApiClient {
    /** 現在のベース URL。デフォルトはビルドタイプ固定値（debug: localhost / release: Koyeb）。 */
    @Volatile
    private var baseUrl: String = BuildConfig.API_BASE_URL

    /** キャッシュ済みの API サービス。[updateBaseUrl] で無効化される。 */
    @Volatile
    private var service: FilmyApiService? = null

    /**
     * 全リクエストに `X-API-Key` ヘッダーを付与する Interceptor。
     * キーは BuildConfig.API_KEY（Koyeb の FILMY_API_KEY と同値）を参照する。
     */
    private val apiKeyInterceptor = Interceptor { chain ->
        val request = chain.request().newBuilder()
            .header("X-API-Key", BuildConfig.API_KEY)
            .build()
        chain.proceed(request)
    }

    /**
     * HTTP ログ出力用 Interceptor。リクエスト/レスポンス本文（現在地 lat/lng 含む）を
     * logcat へ漏らさないため、debug ビルド限定で追加する（release では生成しない）。
     */
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
        // X-API-Key をログへ漏らさないためのヘッダー Redact。
        redactHeader("X-API-Key")
    }

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(apiKeyInterceptor)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(loggingInterceptor)
            }
        }
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    /**
     * 現在のベース URL に対応する API サービスを返す。
     * 未生成ならダブルチェックロックで一度だけ生成・キャッシュする。
     */
    val apiService: FilmyApiService
        get() {
            val cached = service
            if (cached != null) return cached
            synchronized(this) {
                val doubleChecked = service
                if (doubleChecked != null) return doubleChecked
                return buildService(baseUrl).also { service = it }
            }
        }

    /**
     * ベース URL を変更し、キャッシュ済みサービスを無効化する。
     * URL が不正（[HttpUrl] としてパース不可）な場合は [IllegalArgumentException] を投げ、
     * 現在の設定は変更しない。
     *
     * @throws IllegalArgumentException URL が不正な場合
     */
    fun updateBaseUrl(url: String) {
        val normalized = normalizeBaseUrl(url)
        baseUrl = normalized
        service = null
    }

    /** 現在のベース URL を返す。 */
    fun currentBaseUrl(): String = baseUrl

    /**
     * URL を検証し、Retrofit の baseUrl 要件（末尾 `/`）を満たすよう正規化する。
     * パース失敗（スキーム欠落・ホスト不正など）は [IllegalArgumentException] を投げる。
     */
    private fun normalizeBaseUrl(url: String): String {
        val parsed = url.toHttpUrlOrNull()
            ?: throw IllegalArgumentException("URLの形式が正しくありません: $url")
        require(parsed.scheme == "http" || parsed.scheme == "https") {
            "http/https の URL を指定してください: $url"
        }
        return if (url.endsWith("/")) url else url + "/"
    }

    private fun buildService(url: String): FilmyApiService =
        Retrofit.Builder()
            .baseUrl(url)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(FilmyApiService::class.java)
}
