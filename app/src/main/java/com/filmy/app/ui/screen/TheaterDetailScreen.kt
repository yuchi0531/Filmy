package com.filmy.app.ui.screen

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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

/**
 * 劇場詳細画面。上映スケジュールと地図・公式サイトへのリンクを表示する。
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

@Composable
private fun TheaterDetailContent(
    theater: TheaterDetailDto,
    onOpenMap: () -> Unit,
    onNavigateWebView: (String) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
    ) {
        item {
            Text(
                text = theater.name,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
            )
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
                    OutlinedButton(onClick = { onNavigateWebView(theater.url) }) {
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
            Spacer(Modifier.height(20.dp))
            Text(
                text = "上映スケジュール",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
            )
            Spacer(Modifier.height(4.dp))
        }

        if (theater.movies.isEmpty()) {
            item {
                Text(
                    text = "現在上映スケジュールがありません",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            // key を指定しない（位置ベース）ことで、movie_id の重複によるクラッシュを避ける。
            items(theater.movies) { movie ->
                ScheduleRow(movie = movie)
            }
        }
    }
}

/** 映画ポスター＋タイトル＋日付別の上映時刻チップ。 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ScheduleRow(movie: MovieScheduleDto) {
    Column(modifier = Modifier.padding(bottom = 20.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            PosterImage(
                url = movie.poster_url,
                title = movie.movie_title,
                modifier = Modifier.size(width = 56.dp, height = 84.dp),
            )
            Spacer(Modifier.width(12.dp))
            Text(
                text = movie.movie_title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.height(8.dp))
        movie.dates.forEach { (date, times) ->
            Text(
                text = date,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            FlowRow(
                modifier = Modifier.padding(top = 2.dp, bottom = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                times.forEach { time -> TimeChip(time = time) }
            }
        }
    }
}

/** 上映時刻を表示する小さなチップ。 */
@Composable
private fun TimeChip(time: String) {
    Surface(
        shape = MaterialTheme.shapes.small,
        color = MaterialTheme.colorScheme.surfaceVariant,
    ) {
        Text(
            text = time,
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
        )
    }
}