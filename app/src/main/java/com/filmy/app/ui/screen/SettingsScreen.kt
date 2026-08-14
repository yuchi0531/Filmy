package com.filmy.app.ui.screen

import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.filmy.app.BuildConfig
import com.filmy.app.ui.SettingsViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private const val TAG = "SettingsScreen"

/** 近隣検索半径の選択肢（km）。 */
private val RADIUS_OPTIONS = listOf(3.0f, 5.0f, 10.0f, 20.0f)

@Composable
fun SettingsScreen(viewModel: SettingsViewModel = viewModel()) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    val nearbyRadiusKm by viewModel.nearbyRadiusKm.collectAsStateWithLifecycle()
    var statusMessage by remember { mutableStateOf<String?>(null) }

    // エクスポート: SAF で JSON ファイルの作成先を選ばせる。
    val exportLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CreateDocument("application/json")
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            statusMessage = try {
                val json = viewModel.exportFavorites()
                writeText(context, uri, json)
                "お気に入りをエクスポートしました"
            } catch (e: Exception) {
                Log.e(TAG, "export failed", e)
                "エクスポートに失敗しました"
            }
        }
    }

    // インポート: SAF で JSON ファイルを選択させる。
    val importLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        scope.launch {
            statusMessage = try {
                val json = readText(context, uri)
                viewModel.importFavorites(json)
                "お気に入りをインポートしました"
            } catch (e: Exception) {
                Log.e(TAG, "import failed", e)
                "インポートに失敗しました（形式が正しくない可能性があります）"
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text(text = "設定", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(16.dp))

        // ---- セクション1: 近隣検索半径 ----
        SectionTitle("近隣検索半径")
        Text(
            text = "Nearby 画面で現在地から検索する範囲を選択します。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            RADIUS_OPTIONS.forEach { radius ->
                FilterChip(
                    selected = nearbyRadiusKm == radius,
                    onClick = { viewModel.setNearbyRadiusKm(radius) },
                    label = { Text(formatRadius(radius)) },
                )
            }
        }
        Spacer(modifier = Modifier.height(24.dp))

        HorizontalDivider()
        Spacer(modifier = Modifier.height(24.dp))

        // ---- セクション2: お気に入りのバックアップ ----
        SectionTitle("お気に入りのバックアップ")
        Text(
            text = "お気に入りの映画・劇場を JSON ファイルとして書き出し/復元します。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Button(
            onClick = {
                val fileName = "filmy-favorites-${SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())}.json"
                exportLauncher.launch(fileName)
            },
        ) {
            Text("お気に入りをエクスポート")
        }
        Spacer(modifier = Modifier.height(8.dp))
        OutlinedButton(
            onClick = { importLauncher.launch(arrayOf("application/json")) },
        ) {
            Text("お気に入りをインポート")
        }
        statusMessage?.let { message ->
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.primary,
            )
        }
        Spacer(modifier = Modifier.height(24.dp))

        HorizontalDivider()
        Spacer(modifier = Modifier.height(24.dp))

        // ---- セクション3: アプリ情報 ----
        SectionTitle("アプリ情報")
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                InfoRow("バージョン", BuildConfig.VERSION_NAME)
                Spacer(modifier = Modifier.height(8.dp))
                InfoRow("データソース", "Filmarks")
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "本アプリは技術実証目的で、Filmarks のスクレイピングに依存しています。データの正確性は保証されません。",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun SectionTitle(title: String) {
    Text(text = title, style = MaterialTheme.typography.titleMedium)
    Spacer(modifier = Modifier.height(4.dp))
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.weight(1f),
        )
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
    }
}

private fun formatRadius(radius: Float): String =
    if (radius % 1.0f == 0.0f) "${radius.toInt()}km" else "${radius}km"

/** SAF の outputStream にテキストを UTF-8 で書き込む。 */
private suspend fun writeText(context: android.content.Context, uri: android.net.Uri, text: String) =
    withContext(Dispatchers.IO) {
        context.contentResolver.openOutputStream(uri)?.use { output ->
            output.write(text.toByteArray(Charsets.UTF_8))
        } ?: throw IllegalStateException("出力先を開けませんでした")
    }

/** SAF の inputStream から UTF-8 テキストを読み込む。 */
private suspend fun readText(context: android.content.Context, uri: android.net.Uri): String =
    withContext(Dispatchers.IO) {
        context.contentResolver.openInputStream(uri)?.use { input ->
            input.readBytes().toString(Charsets.UTF_8)
        } ?: throw IllegalStateException("ファイルを開けませんでした")
    }
