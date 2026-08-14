package com.filmy.app

import android.app.Application
import com.filmy.app.data.AppContainer
import com.filmy.app.data.local.AppDatabase
import com.filmy.app.data.local.SettingsDataStore

class FilmyApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Room DB のシングルトンをアプリ起動時に初期化する。
        AppContainer.database = AppDatabase.getInstance(this)
        // 設定 DataStore を初期化する。
        AppContainer.settingsDataStore = SettingsDataStore(this)
    }
}