package com.filmy.app.ui.screen

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.filmy.app.data.api.dto.TheaterSummaryDto
import com.filmy.app.ui.NearbyViewModel
import com.filmy.app.ui.UiState
import com.filmy.app.ui.component.ErrorState
import com.filmy.app.ui.component.LoadingState
import com.filmy.app.ui.component.TheaterCard
import com.filmy.app.ui.navigation.Screen
import com.google.android.gms.location.LocationServices
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume

/** 位置情報が取得できない場合のフォールバック座標（東京駅）。 */
private const val DEFAULT_LAT = 35.6812
private const val DEFAULT_LNG = 139.7671

private const val NEARBY_RADIUS_KM = 10.0

/** 自動リフレッシュの間隔（ミリ秒）。 */
private const val REFRESH_INTERVAL_MS = 30_000L

@Composable
fun NearbyScreen(
    navController: NavHostController,
    viewModel: NearbyViewModel = viewModel(),
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val scope = rememberCoroutineScope()

    // 画面が RESUMED の間だけ 30 秒ごとに位置情報+近隣劇場を再取得する。
    // refresh() は最後に取得した座標を再利用して Loading に戻さず更新する。
    // バックグラウンド（STOPPED）に移るとループは停止する。
    val lifecycleOwner = LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            while (true) {
                viewModel.refresh()
                delay(REFRESH_INTERVAL_MS)
            }
        }
    }

    // 位置情報パーミッション要求。拒否された場合もデフォルト座標で検索する。
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        scope.launch {
            if (granted) {
                loadNearbyWithLocation(context, viewModel)
            } else {
                viewModel.loadNearby(DEFAULT_LAT, DEFAULT_LNG, NEARBY_RADIUS_KM)
            }
        }
    }

    LaunchedEffect(Unit) {
        val hasPermission = ContextCompat.checkSelfPermission(
            context, Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (hasPermission) {
            loadNearbyWithLocation(context, viewModel)
        } else {
            permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    when (val state = uiState) {
        is UiState.Loading -> LoadingState()
        // 再試行は常にデフォルト座標ではなく、現在地（パーミッションがあれば）を使う。
        is UiState.Error -> ErrorState(
            message = state.message,
            onRetry = { loadNearbyWithPermission(context, viewModel, scope) },
        )
        is UiState.Success -> NearbyContent(
            latitude = state.data.latitude,
            longitude = state.data.longitude,
            theaters = state.data.theaters,
            onTheaterClick = { theater ->
                val prefecture = theater.prefecture
                val areaId = theater.area_id
                if (prefecture != null && areaId != null) {
                    navController.navigate(Screen.theaterDetail(prefecture, areaId, theater.id))
                }
            },
        )
    }
}

/**
 * 現在地を取得して nearby を呼ぶ。取得できない場合は東京駅のデフォルト座標を使う。
 */
private suspend fun loadNearbyWithLocation(context: Context, viewModel: NearbyViewModel) {
    val location = getCurrentLocation(context.applicationContext)
    if (location != null) {
        viewModel.loadNearby(location.latitude, location.longitude, NEARBY_RADIUS_KM)
    } else {
        viewModel.loadNearby(DEFAULT_LAT, DEFAULT_LNG, NEARBY_RADIUS_KM)
    }
}

/**
 * 位置情報パーミッションに応じて now loading する（初回表示・再試行共通）。
 * パーミッションがあれば現在地を、なければデフォルト座標を使う。
 */
private fun loadNearbyWithPermission(context: Context, viewModel: NearbyViewModel, scope: CoroutineScope) {
    val hasPermission = ContextCompat.checkSelfPermission(
        context, Manifest.permission.ACCESS_FINE_LOCATION
    ) == PackageManager.PERMISSION_GRANTED
    if (hasPermission) {
        scope.launch { loadNearbyWithLocation(context, viewModel) }
    } else {
        viewModel.loadNearby(DEFAULT_LAT, DEFAULT_LNG, NEARBY_RADIUS_KM)
    }
}

@Composable
private fun NearbyContent(
    latitude: Double,
    longitude: Double,
    theaters: List<TheaterSummaryDto>,
    onTheaterClick: (TheaterSummaryDto) -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        Text(
            text = String.format(
                "近くの映画館 緯度 %.4f / 経度 %.4f",
                latitude, longitude
            ),
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            text = if (theaters.isEmpty()) {
                "この範囲に劇場が見つかりませんでした"
            } else {
                "${theaters.size} 件"
            },
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 4.dp, bottom = 8.dp),
        )
        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(theaters, key = { it.id }) { theater ->
                TheaterCard(theater = theater, onClick = { onTheaterClick(theater) })
            }
        }
    }
}

/**
 * FusedLocationProviderClient で現在地を取得する。
 * Play Services なし・失敗・null の場合は null を返す。
 * コルーチンがキャンセルされた場合は isActive 判定でリスナーによる
 * キャンセル済み continuation への resume（リーク/クラッシュ）を防ぐ。
 */
private suspend fun getCurrentLocation(context: Context): Location? =
    try {
        val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)
        suspendCancellableCoroutine { continuation ->
            fusedLocationClient.lastLocation
                .addOnSuccessListener { location ->
                    if (continuation.isActive) continuation.resume(location)
                }
                .addOnFailureListener {
                    if (continuation.isActive) continuation.resume(null)
                }
        }
    } catch (e: Exception) {
        null
    }