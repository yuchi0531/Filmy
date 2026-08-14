package com.filmy.app.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.filmy.app.data.api.dto.MovieSummaryDto
import com.filmy.app.ui.HomeViewModel
import com.filmy.app.ui.UiState
import com.filmy.app.ui.component.ErrorState
import com.filmy.app.ui.component.LoadingState
import com.filmy.app.ui.component.MovieCard
import kotlinx.coroutines.delay

private const val SECTION_NOW = "上映中"
private const val SECTION_COMING = "公開予定"
private const val SECTION_TREND = "トレンド"

/** 自動リフレッシュの間隔（ミリ秒）。 */
private const val REFRESH_INTERVAL_MS = 30_000L

@Composable
fun HomeScreen(viewModel: HomeViewModel = viewModel()) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    // 画面が RESUMED の間だけ 30 秒ごとに再取得する。
    // 初回データは ViewModel の init が load() で取得するため、
    // ループ開始直後に refresh() を実行すると二重取得になる。最初は delay でスキップする。
    // バックグラウンド（STOPPED）に移るとループは停止する。
    val lifecycleOwner = LocalLifecycleOwner.current
    LaunchedEffect(lifecycleOwner) {
        lifecycleOwner.lifecycle.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            while (true) {
                delay(REFRESH_INTERVAL_MS)
                viewModel.refresh()
            }
        }
    }

    when (val state = uiState) {
        is UiState.Loading -> LoadingState()
        is UiState.Error -> ErrorState(message = state.message, onRetry = viewModel::load)
        is UiState.Success -> HomeContent(
            now = state.data.now,
            coming = state.data.coming,
            trend = state.data.trend,
        )
    }
}

@Composable
private fun HomeContent(
    now: List<MovieSummaryDto>,
    coming: List<MovieSummaryDto>,
    trend: List<MovieSummaryDto>,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(vertical = 8.dp),
    ) {
        MovieSection(title = SECTION_NOW, movies = now)
        MovieSection(title = SECTION_COMING, movies = coming)
        MovieSection(title = SECTION_TREND, movies = trend)
    }
}

@Composable
private fun MovieSection(title: String, movies: List<MovieSummaryDto>) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = title,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
        )
        if (movies.isEmpty()) {
            Text(
                text = "表示できる映画がありません",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            )
        } else {
            LazyRow(
                contentPadding = PaddingValues(horizontal = 16.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(movies, key = { it.id }) { movie ->
                    MovieCard(movie = movie)
                }
            }
        }
    }
}