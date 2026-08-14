package com.filmy.app.ui.screen

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Place
import androidx.compose.material.icons.outlined.FavoriteBorder
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.filmy.app.data.api.dto.MovieScheduleDto
import com.filmy.app.data.api.dto.TheaterDetailDto
import com.filmy.app.ui.TheaterDetailViewModel
import com.filmy.app.ui.UiState
import com.filmy.app.ui.component.ErrorState
import com.filmy.app.ui.component.LoadingState
import com.filmy.app.ui.component.PosterImage
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalTime
import kotlinx.coroutines.launch

/** Filmarks の基底URL。theater.url は相対パスなのでここに連結して絶対URLを組み立てる。 */
private const val FILMARKS_BASE_URL = "https://filmarks.com"

/** 日付タブに表示する日数。 */
private const val DATE_TAB_COUNT = 7

/**
 * 劇場詳細画面。日付タブ方式で上映スケジュールと地図・公式サイトへのリンクを表示する。
 */
@Composable
fun TheaterDetailScreen(
    prefecture: String,
    areaId: String,
    theaterId: String,
    onNavigateWebView: (String) -> Unit,
    viewModel: TheaterDetailViewModel = viewModel(),
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // お気に入り状態をリアルタイム反映（DB 更新で再発行される）。
    val isFavoriteFlow = remember(theaterId) { viewModel.isFavorite(theaterId) }
    val isFavorite by isFavoriteFlow.collectAsStateWithLifecycle(initialValue = false)

    // 初回のみ取得する（画面回転時は ViewModel の状態を維持）。
    LaunchedEffect(prefecture, areaId, theaterId) {
        if (uiState is UiState.Loading) {
            viewModel.loadTheaterDetail(prefecture, areaId, theaterId)
        }
    }

    when (val state = uiState) {
        is UiState.Loading -> LoadingState()
        is UiState.Error -> ErrorState(message = state.message, onRetry = viewModel::retry)
        is UiState.Success -> TheaterDetailContent(
            theater = state.data,
            isFavorite = isFavorite,
            onToggleFavorite = { viewModel.toggleFavorite(state.data, prefecture, areaId) },
            onOpenMap = {
                openMap(context, state.data)?.let { message ->
                    Toast.makeText(context, message, Toast.LENGTH_SHORT).show()
                }
            },
            onNavigateWebView = onNavigateWebView,
        )
    }
}

/** map_url（なければ座標）を外部マップアプリで開く。失敗時はエラーメッセージを返し、成功時は null。 */
private fun openMap(context: Context, theater: TheaterDetailDto): String? {
    // map_url は http/https のみ許可。それ以外のスキームは座標表示にフォールバックする。
    if (!theater.map_url.isNullOrBlank() && isHttpUrl(theater.map_url)) {
        return launchMapIntent(context, Intent(Intent.ACTION_VIEW, Uri.parse(theater.map_url)))
    }
    if (theater.latitude != null && theater.longitude != null) {
        return launchMapIntent(
            context,
            Intent(Intent.ACTION_VIEW, Uri.parse("geo:${theater.latitude},${theater.longitude}")),
        )
    }
    return "地図情報がありません"
}

/** マップ表示用インテントを起動する。受信不能・起動失敗時はエラーメッセージを返す。 */
private fun launchMapIntent(context: Context, intent: Intent): String? {
    if (intent.resolveActivity(context.packageManager) == null) {
        return "この地図を開けるアプリがありません"
    }
    return try {
        context.startActivity(intent)
        null
    } catch (e: Exception) {
        "地図を開けませんでした"
    }
}

/** URL が http/https のどちらかかを判定する。 */
private fun isHttpUrl(url: String): Boolean {
    val scheme = Uri.parse(url).scheme?.lowercase()
    return scheme == "http" || scheme == "https"
}

/**
 * theater.url（Filmarks の相対パス、例: `/theaters/tokyo/99/172`）を
 * WebView が読み込める絶対URL（`https://filmarks.com` + url）に組み立てる。
 * すでに絶対URL（http/https）の場合はそのまま返す。
 */
private fun toAbsoluteUrl(url: String): String =
    if (isHttpUrl(url)) url else FILMARKS_BASE_URL + url

/**
 * 日付タブの一覧を生成する。
 * 今日から [DATE_TAB_COUNT] 日分の日付と、上映データに存在する日付をマージして昇順ソートする。
 * 上映データに無い日も含める（当日は「上映なし」表示になる）。
 */
private fun buildDateList(movies: List<MovieScheduleDto>): List<String> {
    val today = LocalDate.now()
    val generated = (0 until DATE_TAB_COUNT).map { today.plusDays(it.toLong()).toString() }
    val scheduleDates = movies.flatMap { it.dates.keys }
    return (generated + scheduleDates).distinct().sorted()
}

/** `2026-08-14` → `8/14 (金)` 形式の表示ラベルに変換する。 */
private fun formatDateLabel(dateStr: String): String {
    val date = LocalDate.parse(dateStr)
    return "${date.monthValue}/${date.dayOfMonth} (${date.dayOfWeek.toJapanese()})"
}

private fun DayOfWeek.toJapanese(): String = when (this) {
    DayOfWeek.MONDAY -> "月"
    DayOfWeek.TUESDAY -> "火"
    DayOfWeek.WEDNESDAY -> "水"
    DayOfWeek.THURSDAY -> "木"
    DayOfWeek.FRIDAY -> "金"
    DayOfWeek.SATURDAY -> "土"
    DayOfWeek.SUNDAY -> "日"
}

/**
 * 指定日時が過去かどうかを判定する。
 * 今日より前の日付、または今日の過去時刻なら true。
 */
private fun isPastTime(dateStr: String, time: String): Boolean {
    val date = LocalDate.parse(dateStr)
    val today = LocalDate.now()
    if (date.isBefore(today)) return true
    if (date.isAfter(today)) return false
    val parts = time.split(":")
    val hour = parts.getOrNull(0)?.toIntOrNull() ?: return false
    val minute = parts.getOrNull(1)?.toIntOrNull() ?: return false
    return LocalTime.of(hour, minute).isBefore(LocalTime.now())
}

/** 選択日の上映作品とその日の時刻リスト。 */
private data class DaySchedule(
    val movie: MovieScheduleDto,
    val times: List<String>,
)

/** [movies] から指定日 [date] に上映がある作品と時刻を抽出する。 */
private fun moviesForDate(movies: List<MovieScheduleDto>, date: String): List<DaySchedule> =
    movies.mapNotNull { movie ->
        movie.dates[date]?.let { times -> DaySchedule(movie, times) }
    }

@Composable
private fun TheaterDetailContent(
    theater: TheaterDetailDto,
    isFavorite: Boolean,
    onToggleFavorite: () -> Unit,
    onOpenMap: () -> Unit,
    onNavigateWebView: (String) -> Unit,
) {
    val dates = remember(theater) { buildDateList(theater.movies) }
    val todayStr = LocalDate.now().toString()
    val todayIndex = remember(dates) { dates.indexOf(todayStr).coerceAtLeast(0) }

    val pagerState = rememberPagerState(initialPage = todayIndex) { dates.size }
    val scope = rememberCoroutineScope()

    Column(modifier = Modifier.fillMaxSize()) {
        TheaterHeader(
            theater = theater,
            isFavorite = isFavorite,
            onToggleFavorite = onToggleFavorite,
            onOpenMap = onOpenMap,
            onNavigateWebView = onNavigateWebView,
        )

        ScrollableTabRow(
            selectedTabIndex = pagerState.currentPage,
            edgePadding = 16.dp,
        ) {
            dates.forEachIndexed { index, date ->
                Tab(
                    selected = pagerState.currentPage == index,
                    onClick = { scope.launch { pagerState.animateScrollToPage(index) } },
                    text = { Text(formatDateLabel(date)) },
                )
            }
        }

        HorizontalPager(
            state = pagerState,
            modifier = Modifier.weight(1f),
        ) { page ->
            DayScheduleList(date = dates[page], movies = theater.movies)
        }
    }
}

/** 劇場名・住所・地図/公式サイトボタン・お気に入りを表示するヘッダー。 */
@Composable
private fun TheaterHeader(
    theater: TheaterDetailDto,
    isFavorite: Boolean,
    onToggleFavorite: () -> Unit,
    onOpenMap: () -> Unit,
    onNavigateWebView: (String) -> Unit,
) {
    Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(
                text = theater.name,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = onToggleFavorite) {
                Icon(
                    imageVector = if (isFavorite) Icons.Filled.Favorite else Icons.Outlined.FavoriteBorder,
                    contentDescription = if (isFavorite) "お気に入りを解除" else "お気に入りに追加",
                    tint = if (isFavorite) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.onSurfaceVariant
                    },
                )
            }
        }
        if (!theater.address.isNullOrBlank()) {
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Filled.Place,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(16.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    text = theater.address,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
        Spacer(Modifier.height(16.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilledTonalButton(onClick = onOpenMap) {
                Icon(
                    imageVector = Icons.Filled.Place,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text("地図を開く")
            }
            if (!theater.url.isNullOrBlank()) {
                OutlinedButton(onClick = { onNavigateWebView(toAbsoluteUrl(theater.url)) }) {
                    Icon(
                        imageVector = Icons.Filled.Language,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp),
                    )
                    Spacer(Modifier.width(6.dp))
                    Text("公式サイトを見る")
                }
            }
        }
    }
}

/** 選択日の上映作品一覧。上映が無い日はメッセージを表示する。 */
@Composable
private fun DayScheduleList(date: String, movies: List<MovieScheduleDto>) {
    val schedules = remember(date, movies) { moviesForDate(movies, date) }

    if (schedules.isEmpty()) {
        Box(
            modifier = Modifier.fillMaxSize().padding(16.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = "この日の上映スケジュールはありません",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    } else {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
        ) {
            // key を指定しない（位置ベース）ことで、movie_id の重複によるクラッシュを避ける。
            items(schedules) { schedule ->
                DayScheduleRow(schedule = schedule, date = date)
            }
        }
    }
}

/** 映画ポスター＋タイトル＋選択日の上映時刻チップ。 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun DayScheduleRow(schedule: DaySchedule, date: String) {
    Column(modifier = Modifier.padding(bottom = 20.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            PosterImage(
                url = schedule.movie.poster_url,
                title = schedule.movie.movie_title,
                modifier = Modifier.size(width = 56.dp, height = 84.dp),
            )
            Spacer(Modifier.width(12.dp))
            Text(
                text = schedule.movie.movie_title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.height(8.dp))
        FlowRow(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            schedule.times.forEach { time ->
                SuggestionChip(
                    onClick = {},
                    enabled = !isPastTime(date, time),
                    label = { Text(time) },
                )
            }
        }
    }
}
