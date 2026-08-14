package com.filmy.app.ui.screen

import android.net.Uri
import android.view.ViewGroup
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.filmy.app.ui.component.ErrorState

/**
 * WebView 画面。ブラウザ風のツールバー（戻る/進む/リロード）とページタイトルを表示する。
 * システムバックではWebViewの履歴があればそれを戻る。
 *
 * セキュリティ上、[shouldOverrideUrlLoading] で http/https 以外のスキーム
 * （javascript:/file:/intent:/about: 等）への遷移を拒否する。
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WebViewScreen(
    url: String,
    onBack: () -> Unit,
) {
    val context = LocalContext.current

    // ページタイトルと履歴の有無をツールバー表示用に保持する。
    var pageTitle by remember(url) { mutableStateOf(url) }
    var canGoBack by remember { mutableStateOf(false) }
    var canGoForward by remember { mutableStateOf(false) }
    // 読み込みエラー時はこれを設定してエラー表示に切り替える。
    var loadError by remember { mutableStateOf<String?>(null) }

    val webView = remember {
        WebView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT,
            )
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                // ローカルファイルアクセスを明示的に無効化する（任意URLロード対策）。
                allowFileAccess = false
                // 複数ウィンドウ（ポップアップ風）の起動を明示的に無効化する。
                setSupportMultipleWindows(false)
            }
            webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, urlString: String?) {
                    pageTitle = view.title?.takeIf { it.isNotBlank() } ?: urlString ?: ""
                    canGoBack = view.canGoBack()
                    canGoForward = view.canGoForward()
                    loadError = null
                }

                // http/https 以外のスキームへの遷移を拒否する。true を返すとそのロードをブロックする。
                // minSdk 26 以降は必ず WebResourceRequest 版が呼ばれる。
                override fun shouldOverrideUrlLoading(
                    view: WebView,
                    request: WebResourceRequest,
                ): Boolean = !isHttpUrl(request.url.toString())

                // サブリソース（画像・広告等）の失敗ではエラー表示しない。
                // メインフレームの失敗のみエラー状態にする。
                override fun onReceivedError(
                    view: WebView,
                    request: WebResourceRequest,
                    error: WebResourceError,
                ) {
                    if (request.isForMainFrame) {
                        loadError = error.description?.toString() ?: "ページを読み込めませんでした"
                    }
                }

                override fun onReceivedHttpError(
                    view: WebView,
                    request: WebResourceRequest,
                    response: WebResourceResponse,
                ) {
                    if (request.isForMainFrame) {
                        loadError = "HTTP ${response.statusCode} エラー"
                    }
                }
            }
        }
    }

    LaunchedEffect(webView, url) {
        when {
            url.isBlank() -> loadError = "読み込むURLがありません"
            !isHttpUrl(url) -> loadError = "サポートされていないURLのため表示できません"
            else -> {
                loadError = null
                webView.loadUrl(url)
            }
        }
    }

    DisposableEffect(webView) {
        onDispose { webView.destroy() }
    }

    BackHandler {
        if (webView.canGoBack()) {
            webView.goBack()
            canGoBack = webView.canGoBack()
            canGoForward = webView.canGoForward()
        } else {
            onBack()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = pageTitle,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "閉じる",
                        )
                    }
                },
                actions = {
                    IconButton(
                        onClick = {
                            webView.goBack()
                            canGoBack = webView.canGoBack()
                            canGoForward = webView.canGoForward()
                        },
                        enabled = canGoBack,
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "戻る",
                        )
                    }
                    IconButton(
                        onClick = {
                            webView.goForward()
                            canGoBack = webView.canGoBack()
                            canGoForward = webView.canGoForward()
                        },
                        enabled = canGoForward,
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = "進む",
                        )
                    }
                    IconButton(
                        onClick = { webView.reload() },
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Refresh,
                            contentDescription = "再読み込み",
                        )
                    }
                },
                // 外側Scaffold（MainActivity）が既にステータスバーのインセットを処理しているため、
                // ここではステータスバー分の余白を二重に取らない。
                windowInsets = WindowInsets(0.dp),
            )
        },
    ) { innerPadding ->
        Box(modifier = Modifier.fillMaxSize().padding(innerPadding)) {
            AndroidView(
                factory = { webView },
                modifier = Modifier.fillMaxSize(),
            )
            loadError?.let { message ->
                ErrorState(message = message, onRetry = { webView.reload() })
            }
        }
    }
}

/** URL が http/https のどちらかかを判定する。 */
private fun isHttpUrl(url: String): Boolean {
    val scheme = Uri.parse(url).scheme?.lowercase()
    return scheme == "http" || scheme == "https"
}