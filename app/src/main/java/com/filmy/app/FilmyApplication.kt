package com.filmy.app

import android.app.Application
import android.util.Log
import com.filmy.app.data.AppContainer
import com.filmy.app.data.api.ApiClient
import com.filmy.app.data.local.AppDatabase
import com.filmy.app.data.local.SettingsDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

class FilmyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Room DB のシングルトンをアプリ起動時に初期化する。
        AppContainer.database = AppDatabase.getInstance(this)
        // 設定 DataStore を初期化する。
        AppContainer.settingsDataStore = SettingsDataStore(this)
        // 保存済みのサーバーURLを復元する（アプリ起動時の一度きり、同期読み込み）。
        restoreApiBaseUrl()
    }

    /**
     * DataStore に保存済みのベース URL を [ApiClient] へ反映する。
     * アプリ起動時に一度だけ同期読み込みするため、初回画面が apiService を取得する前に反映が完了する。
     * 保存値が不正な場合はデフォルトのままにして起動を継続する。
     */
    private fun restoreApiBaseUrl() {
        val saved = try {
            runBlocking { AppContainer.settingsDataStore.apiBaseUrl.first() }
        } catch (e: Exception) {
            Log.w(TAG, "failed to read saved api base url", e)
            return
        }
        if (saved != BuildConfig.API_BASE_URL) {
            try {
                ApiClient.updateBaseUrl(saved)
            } catch (e: IllegalArgumentException) {
                Log.w(TAG, "invalid saved api base url, keeping default", e)
            }
        }
    }

    private companion object {
        const val TAG = "FilmyApplication"
    }
}