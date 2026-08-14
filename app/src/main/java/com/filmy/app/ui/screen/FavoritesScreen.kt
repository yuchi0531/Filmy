package com.filmy.app.ui.screen

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import com.filmy.app.data.api.dto.MovieSummaryDto
import com.filmy.app.data.api.dto.TheaterSummaryDto
import com.filmy.app.data.local.FavoriteMovieEntity
import com.filmy.app.data.local.FavoriteTheaterEntity
import com.filmy.app.ui.FavoritesViewModel
import com.filmy.app.ui.component.MovieCard
import com.filmy.app.ui.component.TheaterCard
import com.filmy.app.ui.navigation.Screen

/** お気に入り画面のタブ。 */
private enum class FavoriteTab(val label: String) {
    Movies("映画"),
    Theaters("劇場"),
}

/**
 * お気に入り一覧画面。タブで映画/劇場を切り替え、各カードから詳細画面へ遷移する。
 */
@Composable
fun FavoritesScreen(
    navController: NavHostController,
    viewModel: FavoritesViewModel = viewModel(),
) {
    val favoriteMovies by viewModel.favoriteMovies.collectAsStateWithLifecycle()
    val favoriteTheaters by viewModel.favoriteTheaters.collectAsStateWithLifecycle()

    var selectedTab by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = selectedTab) {
            FavoriteTab.entries.forEachIndexed { index, tab ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(tab.label) },
                )
            }
        }

        when (FavoriteTab.entries[selectedTab]) {
            FavoriteTab.Movies -> FavoriteMovieList(
                movies = favoriteMovies,
                onMovieClick = { movie ->
                    navController.navigate(Screen.movieDetail(movie.id))
                },
            )
            FavoriteTab.Theaters -> FavoriteTheaterList(
                theaters = favoriteTheaters,
                onTheaterClick = { theater ->
                    // prefecture / areaId が欠落している（旧データ等）場合は不正な
                    // "theater_detail//<id>" ルートを避けるため遷移しない。
                    val prefecture = theater.prefecture
                    val areaId = theater.areaId
                    if (!prefecture.isNullOrBlank() && !areaId.isNullOrBlank()) {
                        navController.navigate(
                            Screen.theaterDetail(
                                prefecture = prefecture,
                                areaId = areaId,
                                theaterId = theater.theaterId,
                            )
                        )
                    }
                },
            )
        }
    }
}

/** お気に入り映画一覧。空の場合は「お気に入りがありません」を表示する。 */
@Composable
private fun FavoriteMovieList(
    movies: List<FavoriteMovieEntity>,
    onMovieClick: (MovieSummaryDto) -> Unit,
) {
    if (movies.isEmpty()) {
        EmptyFavorites()
        return
    }
    LazyRow(
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        items(movies) { favorite ->
            val summary = remember(favorite) { favorite.toSummary() }
            MovieCard(
                movie = summary,
                onClick = { onMovieClick(summary) },
            )
        }
    }
}

/** お気に入り劇場一覧。空の場合は「お気に入りがありません」を表示する。 */
@Composable
private fun FavoriteTheaterList(
    theaters: List<FavoriteTheaterEntity>,
    onTheaterClick: (FavoriteTheaterEntity) -> Unit,
) {
    if (theaters.isEmpty()) {
        EmptyFavorites()
        return
    }
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        items(theaters) { favorite ->
            val summary = remember(favorite) { favorite.toSummary() }
            TheaterCard(
                theater = summary,
                onClick = { onTheaterClick(favorite) },
            )
        }
    }
}

/** お気に入りが一つもない場合のプレースホルダー。 */
@Composable
private fun EmptyFavorites() {
    Box(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "お気に入りがありません",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = "詳細画面のハートボタンから登録できます",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}

private fun FavoriteMovieEntity.toSummary(): MovieSummaryDto = MovieSummaryDto(
    id = movieId,
    title = title,
    rating = rating,
    poster_url = posterUrl,
    release_date = releaseDate,
)

private fun FavoriteTheaterEntity.toSummary(): TheaterSummaryDto = TheaterSummaryDto(
    id = theaterId,
    name = name,
    address = address,
    prefecture = prefecture,
    area_id = areaId,
    url = url,
)