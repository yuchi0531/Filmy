package com.filmy.app.ui.component

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Place
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.filmy.app.data.api.dto.TheaterSummaryDto
import java.util.Locale

/**
 * 劇場カード（名前＋距離＋住所）。
 */
@Composable
fun TheaterCard(
    theater: TheaterSummaryDto,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
) {
    // onClick が null の場合はクリック不可能な Card を使い、リップルを表示しない。
    if (onClick != null) {
        Card(
            modifier = modifier.fillMaxWidth(),
            onClick = onClick,
        ) {
            TheaterCardContent(theater)
        }
    } else {
        Card(
            modifier = modifier.fillMaxWidth(),
        ) {
            TheaterCardContent(theater)
        }
    }
}

@Composable
private fun TheaterCardContent(theater: TheaterSummaryDto) {
    Row(
        modifier = Modifier.padding(16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = Icons.Filled.Place,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
        )
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(start = 12.dp),
        ) {
            Text(
                text = theater.name,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            theater.distance_km?.let { distance ->
                Spacer(Modifier.height(4.dp))
                Text(
                    text = String.format(Locale.ROOT, "%.1f km", distance),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                )
            }
            if (!theater.address.isNullOrBlank()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    text = theater.address,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        }
    }
}