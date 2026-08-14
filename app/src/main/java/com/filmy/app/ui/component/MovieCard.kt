package com.filmy.app.ui.component

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.filmy.app.data.api.dto.MovieSummaryDto

/**
 * 映画カード（ポスター＋タイトル＋評価）。横スクロールリスト用。
 */
@Composable
fun MovieCard(
    movie: MovieSummaryDto,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
) {
    // onClick が null の場合はクリック不可能な Surface を使い、リップルを表示しない。
    if (onClick != null) {
        Surface(
            modifier = modifier.width(110.dp),
            shape = MaterialTheme.shapes.medium,
            color = MaterialTheme.colorScheme.surface,
            onClick = onClick,
        ) {
            MovieCardContent(movie)
        }
    } else {
        Surface(
            modifier = modifier.width(110.dp),
            shape = MaterialTheme.shapes.medium,
            color = MaterialTheme.colorScheme.surface,
        ) {
            MovieCardContent(movie)
        }
    }
}

@Composable
private fun MovieCardContent(movie: MovieSummaryDto) {
    Column(modifier = Modifier.padding(0.dp)) {
        PosterImage(
            url = movie.poster_url,
            title = movie.title,
            modifier = Modifier
                .fillMaxWidth()
                .aspectRatio(2f / 3f),
        )
        Column(modifier = Modifier.padding(6.dp)) {
            Text(
                text = movie.title,
                style = MaterialTheme.typography.bodySmall,
                fontWeight = FontWeight.Medium,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(2.dp))
            RatingBar(rating = movie.rating)
        }
    }
}

/**
 * ポスター画像。URL が null の場合はプレースホルダーを表示する。
 */
@Composable
fun PosterImage(
    url: String?,
    title: String,
    modifier: Modifier = Modifier,
) {
    if (url != null) {
        AsyncImage(
            model = url,
            contentDescription = title,
            contentScale = ContentScale.Crop,
            modifier = modifier,
        )
    } else {
        Box(
            modifier = modifier
                .background(MaterialTheme.colorScheme.surfaceVariant),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                imageVector = Icons.Filled.Movie,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}