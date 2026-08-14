package com.filmy.app.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.filmy.app.data.api.dto.CastMember
import com.filmy.app.data.api.dto.MovieDetailDto
import com.filmy.app.data.api.dto.StreamingInfo
import com.filmy.app.ui.MovieDetailViewModel
import com.filmy.app.ui.UiState
import com.filmy.app.ui.component.ErrorState
import com.filmy.app.ui.component.LoadingState
import com.filmy.app.ui.component.PosterImage
import com.filmy.app.ui.component.RatingBar

/**
 * 映画詳細画面。ポスター、基本情報、あらすじ、監督・キャスト、公式サイト、配信情報を表示する。
 */
@Composable
fun MovieDetailScreen(
    movieId: String,
    onNavigateWebView: (String) -> Unit,
    viewModel: MovieDetailViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // 初回のみ取得する（画面回転時は ViewModel の状態を維持）。
    LaunchedEffect(movieId) {
        if (uiState is UiState.Loading) {
            viewModel.loadMovieDetail(movieId)
        }
    }

    when (val state = uiState) {
        is UiState.Loading -> LoadingState()
        is UiState.Error -> ErrorState(message = state.message, onRetry = viewModel::retry)
        is UiState.Success -> MovieDetailContent(
            movie = state.data,
            onNavigateWebView = onNavigateWebView,
        )
    }
}

@Composable
private fun MovieDetailContent(
    movie: MovieDetailDto,
    onNavigateWebView: (String) -> Unit,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp),
    ) {
        item {
            PosterImage(
                url = movie.poster_url,
                title = movie.title,
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(2f / 3f),
            )
        }
        item {
            Column(modifier = Modifier.padding(horizontal = 16.dp)) {
                Text(
                    text = movie.title,
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold,
                )
                if (!movie.original_title.isNullOrBlank()) {
                    Spacer(Modifier.height(2.dp))
                    Text(
                        text = movie.original_title,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                // 評価
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(top = 8.dp),
                ) {
                    RatingBar(rating = movie.rating, starTint = MaterialTheme.colorScheme.primary)
                    movie.review_count?.let { count ->
                        Spacer(Modifier.width(6.dp))
                        Text(
                            text = "($count 件のレビュー)",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }

                // 公開日・上映時間
                Row(
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    modifier = Modifier.padding(top = 8.dp),
                ) {
                    movie.release_date?.let {
                        InfoItem(icon = Icons.Filled.DateRange, text = "公開日: $it")
                    }
                    movie.runtime?.let {
                        InfoItem(icon = Icons.Filled.Schedule, text = "上映時間: $it")
                    }
                }

                // ジャンル
                if (movie.genres.isNotEmpty()) {
                    Spacer(Modifier.height(12.dp))
                    GenreChips(genres = movie.genres)
                }

                // あらすじ
                if (!movie.synopsis.isNullOrBlank()) {
                    SectionTitle(text = "あらすじ")
                    Text(
                        text = movie.synopsis,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }

                // 監督
                if (movie.director.isNotEmpty()) {
                    SectionTitle(text = "監督")
                    Text(
                        text = movie.director.joinToString("、"),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }

                // キャスト
                if (movie.cast.isNotEmpty()) {
                    SectionTitle(text = "キャスト")
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        movie.cast.forEach { member -> CastLine(member = member) }
                    }
                }

                // 公式サイト
                if (!movie.official_site.isNullOrBlank()) {
                    Spacer(Modifier.height(20.dp))
                    OutlinedButton(onClick = { onNavigateWebView(movie.official_site) }) {
                        Icon(
                            imageVector = Icons.Filled.Language,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(Modifier.width(6.dp))
                        Text("公式サイトを見る")
                    }
                }

                // 配信情報
                if (movie.streaming.isNotEmpty()) {
                    SectionTitle(text = "配信情報")
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        movie.streaming.forEach { info -> StreamingItem(info = info) }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionTitle(text: String) {
    Text(
        text = text,
        style = MaterialTheme.typography.titleMedium,
        fontWeight = FontWeight.Bold,
        modifier = Modifier.padding(top = 20.dp, bottom = 4.dp),
    )
}

@Composable
private fun InfoItem(icon: ImageVector, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(16.dp),
        )
        Spacer(Modifier.width(6.dp))
        Text(text = text, style = MaterialTheme.typography.bodyMedium)
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun GenreChips(genres: List<String>) {
    FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        genres.forEach { genre ->
            AssistChip(onClick = {}, label = { Text(genre) })
        }
    }
}

@Composable
private fun CastLine(member: CastMember) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = member.name,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        member.character?.let { character ->
            Spacer(Modifier.width(8.dp))
            Text(
                text = character,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun StreamingItem(info: StreamingInfo) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = info.service,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = info.type,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}