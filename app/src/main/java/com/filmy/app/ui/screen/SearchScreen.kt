package com.filmy.app.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.filmy.app.data.api.dto.MovieSummaryDto
import com.filmy.app.ui.SearchViewModel
import com.filmy.app.ui.UiState
import com.filmy.app.ui.component.ErrorState
import com.filmy.app.ui.component.LoadingState
import com.filmy.app.ui.component.PosterImage
import com.filmy.app.ui.component.RatingBar

@Composable
fun SearchScreen(viewModel: SearchViewModel = viewModel()) {
    val query by viewModel.query.collectAsStateWithLifecycle()
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Column(modifier = Modifier.fillMaxSize().padding(16.dp)) {
        // 検索バー
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = viewModel::onQueryChange,
                modifier = Modifier.weight(1f),
                placeholder = { Text("映画のタイトルを検索") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { viewModel.search() }),
            )
            IconButton(onClick = viewModel::search) {
                Icon(
                    imageVector = Icons.Filled.Search,
                    contentDescription = "検索",
                    modifier = Modifier.size(28.dp),
                )
            }
        }

        when (val state = uiState) {
            is UiState.Loading -> LoadingState()
            is UiState.Error -> ErrorState(message = state.message, onRetry = viewModel::search)
            is UiState.Success -> SearchResults(
                movies = state.data.results,
                heading = state.data.heading,
                total = state.data.total,
            )
        }
    }
}

@Composable
private fun SearchResults(
    movies: List<MovieSummaryDto>,
    heading: String?,
    total: Int,
) {
    Column(modifier = Modifier.fillMaxSize().padding(top = 8.dp)) {
        val summary = if (movies.isEmpty()) {
            "該当する映画が見つかりませんでした"
        } else {
            heading ?: "検索結果 ${movies.size} 件"
        }
        Text(
            text = summary,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        LazyColumn(
            modifier = Modifier.padding(top = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(movies, key = { it.id }) { movie ->
                MovieRow(movie = movie)
            }
        }
    }
}

/** 検索結果の横長カード（ポスター＋タイトル＋評価）。 */
@Composable
private fun MovieRow(movie: MovieSummaryDto) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        PosterImage(
            url = movie.poster_url,
            title = movie.title,
            modifier = Modifier.size(width = 60.dp, height = 90.dp),
        )
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(start = 12.dp),
        ) {
            Text(
                text = movie.title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            movie.release_date?.let { releaseDate ->
                Text(
                    text = releaseDate,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Spacer(Modifier.height(4.dp))
            RatingBar(rating = movie.rating)
        }
    }
}