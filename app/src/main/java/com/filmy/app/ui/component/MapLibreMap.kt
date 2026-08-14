package com.filmy.app.ui.component

import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import org.maplibre.android.MapLibre
import org.maplibre.android.WellKnownTileServer
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.geometry.LatLngBounds
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.Point

/**
 * 地図上に立てる劇場ピンのデータ。
 */
data class MapTheaterPin(
    val id: String,
    val name: String,
    val latitude: Double,
    val longitude: Double,
)

/** OpenFreeMap のスタイル（APIキー不要・無料）。 */
private const val STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"

private const val CURRENT_SOURCE_ID = "current-location-source"
private const val CURRENT_LAYER_ID = "current-location-layer"
private const val CURRENT_COLOR = "#1e88e5"

private const val THEATERS_SOURCE_ID = "theaters-source"
private const val THEATERS_LAYER_ID = "theaters-layer"
private const val THEATER_COLOR = "#e91e63"

/** 劇場が無い場合のフォールバックズーム。 */
private const val DEFAULT_ZOOM = 12.0

/** 劇場ピンまで含めたカメラフィット時の余白（dp）。 */
private const val PADDING_DP = 64f

/**
 * MapLibre GL Native の MapView を Compose で包む Composable。
 * 現在地（中心座標）と劇場ピンを CircleLayer で表示する。
 * ピンは画像アセット不要の GeoJsonSource + CircleLayer で描画する。
 */
@Composable
fun MapLibreMap(
    centerLat: Double,
    centerLng: Double,
    theaters: List<MapTheaterPin>,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val density = context.resources.displayMetrics.density

    // MapLibre 13.x では MapView 生成前に getInstance による初期化が必須。
    // OpenFreeMap はカスタムタイルサーバのため APIキー不要（空文字）。
    val mapView = remember {
        if (!MapLibre.hasInstance()) {
            MapLibre.getInstance(context, "", WellKnownTileServer.MapLibre)
        }
        MapView(context)
    }
    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var style by remember { mutableStateOf<Style?>(null) }

    // MapView 破棄済みフラグ。ON_DESTROY と onDispose の両方から onDestroy() が
    // 二重に呼ばれるのを防ぎ、破棄後に発火した getMapAsync コールバックが
    // 破棄済みビューを触らないようにするためのガード。
    var destroyed by remember { mutableStateOf(false) }

    // mapView.onDestroy() を一度だけ呼ぶ。
    val destroyMapView = {
        if (!destroyed) {
            destroyed = true
            mapView.onDestroy()
        }
    }

    // MapView のライフサイクルをホストの LifecycleOwner に委譲する。
    // DisposableEffect 実行時点では既に RESUMED のため onCreate/onStart/onResume を明示呼び出しし、
    // 以降の遷移は LifecycleEventObserver で追従する。
    DisposableEffect(lifecycleOwner) {
        mapView.onCreate(null)
        mapView.onStart()
        mapView.onResume()

        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                Lifecycle.Event.ON_DESTROY -> destroyMapView()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)

        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            destroyMapView()
        }
    }

    AndroidView(modifier = modifier, factory = { mapView })

    // スタイルは一度だけロードする。
    DisposableEffect(mapView) {
        mapView.getMapAsync { mapInstance ->
            // コールバック発火前にビューが破棄されていた場合は何もしない。
            if (destroyed) return@getMapAsync
            map = mapInstance
            mapInstance.setStyle(STYLE_URL) { styleInstance ->
                if (!destroyed) style = styleInstance
            }
        }
        onDispose { /* MapView の破棄はライフサイクル側で処理済み */ }
    }

    // スタイルロード後、中心座標・劇場リストの変更に応じてソース・レイヤー・カメラを更新する。
    // theaters は再コンポジションのたびに新しい List インスタンスになり得るため、
    // 内容ベースのキーを生成し、データが実質変わらない場合はカメラ再フィットを抑止する。
    val theatersKey = remember(theaters) {
        theaters.map { "${it.id}:${it.latitude}:${it.longitude}" }.joinToString(",")
    }
    LaunchedEffect(map, style, centerLat, centerLng, theatersKey) {
        val currentMap = map ?: return@LaunchedEffect
        val currentStyle = style ?: return@LaunchedEffect
        updatePins(currentStyle, currentMap, centerLat, centerLng, theaters, density)
    }
}

/**
 * 現在地・劇場のピン（GeoJsonSource + CircleLayer）を更新し、カメラをピン全体にフィットさせる。
 * すでにソースが存在する場合はジオメトリのみ差し替えてレイヤーの重複追加を避ける。
 */
private fun updatePins(
    style: Style,
    map: MapLibreMap,
    centerLat: Double,
    centerLng: Double,
    theaters: List<MapTheaterPin>,
    density: Float,
) {
    // 現在地ピン（中心座標）。
    val currentPoint = Feature.fromGeometry(Point.fromLngLat(centerLng, centerLat))
    val currentSource = style.getSource(CURRENT_SOURCE_ID) as? GeoJsonSource
    if (currentSource == null) {
        style.addSource(GeoJsonSource(CURRENT_SOURCE_ID, currentPoint))
        style.addLayer(
            CircleLayer(CURRENT_LAYER_ID, CURRENT_SOURCE_ID).withProperties(
                PropertyFactory.circleColor(CURRENT_COLOR),
                PropertyFactory.circleRadius(8f),
                PropertyFactory.circleStrokeColor("#ffffff"),
                PropertyFactory.circleStrokeWidth(2f),
            )
        )
    } else {
        currentSource.setGeoJson(currentPoint)
    }

    // 劇場ピン。
    val theaterFeatures = theaters.map {
        Feature.fromGeometry(Point.fromLngLat(it.longitude, it.latitude))
    }
    val theaterCollection = FeatureCollection.fromFeatures(theaterFeatures)
    val theaterSource = style.getSource(THEATERS_SOURCE_ID) as? GeoJsonSource
    if (theaterSource == null) {
        style.addSource(GeoJsonSource(THEATERS_SOURCE_ID, theaterCollection))
        style.addLayer(
            CircleLayer(THEATERS_LAYER_ID, THEATERS_SOURCE_ID).withProperties(
                PropertyFactory.circleColor(THEATER_COLOR),
                PropertyFactory.circleRadius(6f),
                PropertyFactory.circleStrokeColor("#ffffff"),
                PropertyFactory.circleStrokeWidth(1.5f),
            )
        )
    } else {
        theaterSource.setGeoJson(theaterCollection)
    }

    // カメラ: 中心座標と劇場ピンをすべて収める。劇場が無ければ中心座標にズーム。
    val camera = if (theaters.isEmpty()) {
        CameraPosition.Builder()
            .target(LatLng(centerLat, centerLng))
            .zoom(DEFAULT_ZOOM)
            .build()
    } else {
        val bounds = LatLngBounds.Builder()
            .include(LatLng(centerLat, centerLng))
            .apply { theaters.forEach { include(LatLng(it.latitude, it.longitude)) } }
            .build()
        val paddingPx = (PADDING_DP * density).toInt()
        map.getCameraForLatLngBounds(
            bounds,
            intArrayOf(paddingPx, paddingPx, paddingPx, paddingPx),
        ) ?: CameraPosition.Builder()
            .target(LatLng(centerLat, centerLng))
            .zoom(DEFAULT_ZOOM)
            .build()
    }
    map.moveCamera(CameraUpdateFactory.newCameraPosition(camera))
}
