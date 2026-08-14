package com.filmy.app.ui.screen

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val TAG = "SettingsScreen"

/** プレビューとして読み込む最大バイト数。 */
private const val MAX_PREVIEW_BYTES = 4096

@Composable
fun SettingsScreen() {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var selectedUri by remember { mutableStateOf<Uri?>(null) }
    var displayName by remember { mutableStateOf<String?>(null) }
    var contentPreview by remember { mutableStateOf<String?>(null) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // SAF: 任意のファイル（*/*）を選択するためのランチャー。
    val filePickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        selectedUri = uri
        errorMessage = null
        // 再起動後も読み取れるよう persistable URI permission を取得（失敗してもログのみ）。
        takePersistableReadPermission(context, uri)
        // 読み取りは IO スレッドで（ContentResolver 経由のテキスト読み取り）。
        // 名前とプレビューを独立に読み、片方の失敗がもう片方の結果を失わせないようにする。
        scope.launch {
            errorMessage = null
            val nameResult = runCatching { queryDisplayName(context, uri) }
            val previewResult = runCatching { readTextPreview(context, uri) }

            displayName = nameResult.getOrNull()
                ?: uri.pathSegments.lastOrNull()
                ?: "(不明)"

            previewResult.getOrNull()?.let { contentPreview = it }

            val failures = buildList {
                if (nameResult.isFailure) add("ファイル名の取得に失敗")
                if (previewResult.isFailure) add("内容の読み込みに失敗")
            }
            if (failures.isNotEmpty()) {
                errorMessage = failures.joinToString(" / ")
                Log.w(TAG, "ファイル読み込みの一部失敗 uri=$uri, name=$displayName, failures=$failures", nameResult.exceptionOrNull() ?: previewResult.exceptionOrNull())
            } else {
                Log.d(TAG, "ファイル読み込み完了 uri=$uri, name=$displayName")
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
    ) {
        Text(text = "設定", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "Storage Access Framework でファイルを選択し、内容を読み取ります。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(modifier = Modifier.height(16.dp))

        Button(onClick = { filePickerLauncher.launch(arrayOf("*/*")) }) {
            Text("ファイルを選択")
        }
        Spacer(modifier = Modifier.height(24.dp))

        errorMessage?.let { message ->
            Text(
                text = message,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.error,
            )
            Spacer(modifier = Modifier.height(16.dp))
        }

        selectedUri?.let { uri ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(text = "選択中のファイル", style = MaterialTheme.typography.titleMedium)
                    Spacer(modifier = Modifier.height(8.dp))
                    InfoRow(label = "表示名", value = displayName ?: "(不明)")
                    Spacer(modifier = Modifier.height(4.dp))
                    InfoRow(label = "URI", value = uri.toString())
                }
            }
            Spacer(modifier = Modifier.height(16.dp))

            contentPreview?.let { preview ->
                Card(modifier = Modifier.fillMaxWidth()) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(text = "内容プレビュー", style = MaterialTheme.typography.titleMedium)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = preview.ifEmpty { "(読み取れるテキストがありません)" },
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Text(
        text = "$label: $value",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

/** DISPLAY_NAME を ContentResolver 経由で取得する。無ければ null。 */
private suspend fun queryDisplayName(context: Context, uri: Uri): String? =
    withContext(Dispatchers.IO) {
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val columnIndex = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (columnIndex >= 0) cursor.getString(columnIndex) else null
            } else {
                null
            }
        }
    }

/** 先頭 MAX_PREVIEW_BYTES バイトを UTF-8 で読み、プレビュー文字列を返す。 */
private suspend fun readTextPreview(context: Context, uri: Uri): String =
    withContext(Dispatchers.IO) {
        context.contentResolver.openInputStream(uri)?.use { input ->
            val buffer = ByteArray(MAX_PREVIEW_BYTES)
            val read = input.read(buffer)
            String(buffer, 0, read.coerceAtLeast(0), Charsets.UTF_8)
        } ?: ""
    }

/** 再起動後にもアクセスできるよう persistable URI permission を取得する。 */
private fun takePersistableReadPermission(context: Context, uri: Uri) {
    try {
        context.contentResolver.takePersistableUriPermission(
            uri, Intent.FLAG_GRANT_READ_URI_PERMISSION
        )
        Log.d(TAG, "persistable URI permission 取得: $uri")
    } catch (e: SecurityException) {
        // プロバイダーが persistable permission をサポートしない場合はログのみ。
        Log.w(TAG, "persistable URI permission を取得できません: $uri", e)
    }
}