package com.filmy.app.ui.component

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import java.util.Locale

/**
 * 星アイコン＋評価値の表示。
 * rating が null の場合は何も表示しない。
 */
@Composable
fun RatingBar(
    rating: Double?,
    modifier: Modifier = Modifier,
    starTint: Color = Color(0xFFFFB300),
) {
    if (rating == null) return
    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        Icon(
            imageVector = Icons.Filled.Star,
            contentDescription = "評価",
            tint = starTint,
            modifier = Modifier.size(14.dp),
        )
        Spacer(Modifier.width(2.dp))
        Text(
            text = String.format(Locale.ROOT, "%.1f", rating),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
        )
    }
}