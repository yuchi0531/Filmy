package com.filmy.app.data.local

import android.content.Context
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

/** アプリ設定を永続化する Preferences DataStore の拡張プロパティ（単一インスタンス）。 */
private val Context.settingsDataStore by preferencesDataStore(name = "settings")

/**
 * アプリ設定を Preferences DataStore で読み書きするリポジトリ。
 * 現在は「近隣検索半径（km）」のみ保持する。
 */
class SettingsDataStore(private val context: Context) {

    /** 近隣検索の半径（km）。デフォルト 10.0。 */
    val nearbyRadiusKm: Flow<Float> = context.settingsDataStore.data
        .map { preferences -> preferences[KEY_NEARBY_RADIUS_KM] ?: DEFAULT_RADIUS_KM }

    /** 近隣検索の半径（km）を保存する。 */
    suspend fun setNearbyRadiusKm(radius: Float) {
        context.settingsDataStore.edit { preferences ->
            preferences[KEY_NEARBY_RADIUS_KM] = radius
        }
    }

    private companion object {
        val KEY_NEARBY_RADIUS_KM = floatPreferencesKey("nearby_radius_km")
        const val DEFAULT_RADIUS_KM = 10.0f
    }
}
