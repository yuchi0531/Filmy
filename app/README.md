# Filmy Android App

Filmarks の映画情報を検索・閲覧する **Android アプリ**（Kotlin + Jetpack Compose + Material 3）。

バックエンドAPI（FastAPI on Koyeb）を介してデータを取得する。アプリ自体は Filmarks に
直接アクセスしない。

## 主な機能

- **Home**: 上映中・公開予定・トレンドの映画を横スクロール表示
- **Nearby**: 現在地周辺の映画館を検索（FusedLocation。失敗時は東京駅にフォールバック）
- **Search**: 映画キーワード検索
- **Movie Detail**: ポスター・あらすじ・監督/キャスト・評価・配信情報・公式サイト（WebView）
- **Theater Detail**: 劇場情報・上映スケジュール・地図リンク・公式サイト（WebView）
- **Favorites**: お気に入り映画/劇場の永続化（Room）

## 技術スタック

| 項目 | 技術 |
| --- | --- |
| 言語 / UI | Kotlin 2.2 + Jetpack Compose + Material 3 |
| アーキテクチャ | MVVM（ViewModel + Repository + sealed UiState） |
| ネットワーク | Retrofit 2.11 + OkHttp 4.12 + Gson |
| 画像 | Coil 2.7（`AsyncImage`、メモリ＋ディスクキャッシュ） |
| 永続化 | Room 2.7.2（お気に入り） |
| 位置情報 | Google Play Services Location 21.3.0 |
| ナビゲーション | Navigation Compose 2.8.5 |

- 要件: JDK 17 / Android SDK（compileSdk 35, minSdk 26, targetSdk 35）
- 依存関係は `gradle/libs.versions.toml` のバージョンカタログで一元管理

## セットアップ

### ビルド

リポジトリルートで実行（`settings.gradle.kts` が `app` を含む）:

```bash
# ルートから
gradle :app:assembleDebug
```

出力 APK: `app/build/outputs/apk/debug/app-debug.apk`

### エミュレータでの実行

1. Android Studio でルートディレクトリを開く
2. エミュレータ（API 26+）を起動
3. バックエンドをローカルで起動（下記）
4. `Run` ボタンで `app` を実行

**バックエンドをローカルで起動（必須）:**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## ベースURL設定

Android アプリのAPIベースURLはビルドタイプごとに `app/build.gradle.kts` の
`buildConfigField` で定義し、`data/api/ApiClient.kt` が `BuildConfig.API_BASE_URL` を参照する:

```kotlin
// app/build.gradle.kts
buildTypes {
    debug { buildConfigField("String", "API_BASE_URL", "\"http://10.0.2.2:8000/\"") }
    release { buildConfigField("String", "API_BASE_URL", "\"https://filmy.koyeb.app/\"") }
}
```

- **debug**: `http://10.0.2.2:8000/` — `10.0.2.2` は Android エミュレータからホストマシンの
  `localhost` を指す特殊アドレス。（物理端末で試す場合はホストの LAN IP に変更し、同一ネットワークへ接続すること。）
- **release**: `https://filmy.koyeb.app/`（Koyeb のデプロイURL、仮）
- バックエンドは `0.0.0.0:8000` で起動すること（`--host 0.0.0.0`）。

### 平文通信（cleartext）の許可

`res/xml/network_security_config.xml` で、**平文通信（http）はデフォルトで禁止**し、
エミュレータ開発用の `http://10.0.2.2:8000`（ホストの localhost）のみを
`domain-config` で例外的に許可している。`AndroidManifest.xml` の
`usesCleartextTraffic="false"` と併用して、本番環境では https 通信のみに制限される。

## プロジェクト構成

```
app/src/main/java/com/filmy/app/
├── MainActivity.kt                 # ボトムナビゲーション＋NavGraph
├── FilmyApplication.kt             # Application（AppDatabase 初期化）
├── data/
│   ├── api/
│   │   ├── ApiClient.kt            # BASE_URL, Retrofit/OkHttp 設定
│   │   ├── FilmyApiService.kt      # バックエンドAPI定義
│   │   └── dto/                    # バックエンドPydanticモデルと一致するDTO
│   ├── local/                      # Room（FavoriteMovie/ Theater entity+DAO, AppDatabase）
│   ├── repository/                 # Movie/Theater/Favorite 各Repository
│   └── AppContainer.kt             # 簡易DIコンテナ
├── ui/
│   ├── UiState.kt                  # sealed interface (Loading/Success/Error)
│   ├── HomeViewModel / NearbyViewModel / SearchViewModel
│   ├── MovieDetailViewModel / TheaterDetailViewModel / FavoritesViewModel
│   ├── component/                  # MovieCard / TheaterCard / RatingBar / LoadingState / ErrorState
│   ├── screen/                     # Home / Nearby / Search / Detail×2 / Favorites / Settings / WebView
│   ├── navigation/NavGraph.kt      # Screen 列挙＋ルート定義
│   └── theme/                      # Color / Theme / Type
```

### DTO とバックエンドモデルの整合

Android の `data/api/dto/` はバックエンドの Pydantic モデル（`backend/app/models/`）と
**snake_case で完全一致**させている。バックエンドのレスポンス構造を変更する場合は
併せて更新すること。

## 参考

- バックエンド設計・API 一覧: [backend/README.md](../backend/README.md) / [backend/API.md](../backend/API.md)
- プロジェクト全体: [ルート README](../README.md)