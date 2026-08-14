# Filmy

[Filmarks](https://filmarks.com) の映画・劇場・上映スケジュール情報をスクレイピングして提供する
**映画館スケジュール検索アプリ** のモノレポプロジェクトです。

- **backend/**: FastAPI 製のスクレイピングAPIサーバー（Filmarks をクロールして JSON を返す）
- **app/**: Android アプリ（Kotlin + Jetpack Compose + Material 3、バックエンドAPIを利用）

```
┌─────────────┐   HTTPS / REST JSON    ┌──────────────────────┐
│  Android    │ ─────────────────────▶ │  Backend (FastAPI)   │
│  (Compose)  │ ◀───────────────────── │  (Koyeb デプロイ)    │
└─────────────┘       JSON レスポンス   └──────────┬───────────┘
                                                   │ スクレイピング
                                                   ▼
                                            ┌─────────────┐
                                            │  Filmarks   │
                                            └─────────────┘
```

- Android アプリは直接 Filmarks にアクセスせず、**バックエンドAPI経由**でデータを取得します。
- バックエンドは Filmarks へのアクセス間隔をプロセス共有で5秒に制限し、結果をインメモリキャッシュします。

## モノレポ構造

```
filmy/
├── backend/                  # FastAPI バックエンド（Python 3.12+）
│   ├── app/
│   │   ├── main.py           # FastAPIインスタンス、CORS、ルート登録
│   │   ├── config.py         # pydantic-settings（FILMY_ プレフィックス）
│   │   ├── routers/          # movies / theaters / search ルーター
│   │   ├── scrapers/         # Filmarks スクレイピング実装
│   │   ├── models/           # Pydantic レスポンスモデル
│   │   └── cache/            # cachetools によるTTLキャッシュ
│   ├── tests/                # pytest（単体＋結合テスト 121件）
│   ├── Dockerfile            # python:3.12-slim（ポート8080）
│   └── requirements.txt
├── app/                      # Android アプリ（Kotlin + Compose）
│   └── src/main/java/com/filmy/app/
│       ├── data/             # Retrofit API / DTO / Room（お気に入り）
│       ├── ui/               # ViewModel / Screen / Component
│       └── MainActivity.kt   # ボトムナビゲーション＋NavGraph
├── gradle/                   # Gradle バージョンカタログ
└── README.md
```

## 技術スタック

### バックエンド

| 項目 | 技術 |
| --- | --- |
| フレームワーク | FastAPI (Python 3.12) |
| HTTP クライアント | httpx（ブラウザ風ヘッダー、フォールバック付き） |
| HTML パース | BeautifulSoup4 + lxml |
| キャッシュ | cachetools（TTLCache、名前空間別） |
| 設定 | pydantic-settings（環境変数 `FILMY_*`） |
| テスト | pytest + fastapi.testclient |
| デプロイ | Docker → Koyeb |

### Android

| 項目 | 技術 |
| --- | --- |
| 言語 / UI | Kotlin 2.2 + Jetpack Compose + Material 3 |
| アーキテクチャ | MVVM（ViewModel + Repository + sealed UiState） |
| ネットワーク | Retrofit + OkHttp + Gson |
| 画像 | Coil（メモリ＋ディスクキャッシュ） |
| 永続化 | Room（お気に入り登録） |
| 位置情報 | Google Play Services Location |
| ナビゲーション | Navigation Compose |

## セットアップ手順

### バックエンド（ローカル開発）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 開発サーバー起動
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

動作確認:

```bash
curl http://localhost:8000/health
# => {"status":"ok"}
curl http://localhost:8000/api/movies/now
```

詳細は [backend/README.md](backend/README.md) と [backend/API.md](backend/API.md) を参照してください。

### Android

要件: JDK 17 / Android SDK（API 35）

```bash
# ルート（gradle/libs.versions.toml）からビルド
gradle :app:assembleDebug
```

APK は `app/build/outputs/apk/debug/app-debug.apk` に出力されます。
詳細は [app/README.md](app/README.md) を参照してください。

## テスト

### バックエンド（121件: 単体99件 + 結合22件）

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

結合テスト（`tests/test_integration.py`）は **実ネットワークに一切アクセスせず**、
モッククライアント（`tests/fake_client.py`）経由で全APIエンドポイントを検証します。

## デプロイ手順（Koyeb）

バックエンドは Docker コンテナとして Koyeb（無料常駐インスタンス: 512MB / 0.1vCPU / 2GB）にデプロイします。

```bash
# Koyeb CLI をインストール
curl -fsSL https://raw.githubusercontent.com/koyeb/cli/master/install.sh | sh
koyeb login

cd backend
koyeb app create filmy
koyeb service create filmy --docker . --port 8080
```

- ポート: `8080`（Dockerfile の `EXPOSE 8080`）
- ヘルスチェック: `GET /health`
- 環境変数は `koyeb secret create FILMY_XXX=...` で設定可能

注意: Koyeb の無料枠は利用開始時にクレジットカード登録が必要です。
また、スクレイピング間隔（`FILMY_REQUEST_INTERVAL`、デフォルト5秒）は必ず守ってください。

## APIエンドポイント一覧

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/health` | ヘルスチェック |
| GET | `/api/movies/now` | 上映中の映画一覧（`?page=`） |
| GET | `/api/movies/coming` | 公開予定の映画一覧 |
| GET | `/api/movies/upcoming` | 今週公開の映画一覧 |
| GET | `/api/movies/trend` | トレンドの映画一覧 |
| GET | `/api/movies/{movie_id}` | 映画詳細（movie_id は数字のみ） |
| GET | `/api/search?q=` | 映画検索（1〜200文字） |
| GET | `/api/theaters/{prefecture}` | 都道府県のエリア一覧（例: `tokyo`） |
| GET | `/api/theaters/{prefecture}/{area_id}` | エリアの劇場一覧 |
| GET | `/api/theaters/{prefecture}/{area_id}/{theater_id}` | 劇場詳細＋上映スケジュール |
| GET | `/api/theaters/nearby?lat=&lng=&radius=` | 近隣劇場検索（radius 1〜100km） |

パラメータ・レスポンス例・エラーコードの詳細は [backend/API.md](backend/API.md) を参照してください。

## 注意事項

- 本プロジェクトは **Filmarks のスクレイピング** により情報を取得します。
  利用時は [Filmarks 利用規約](https://filmarks.com/terms) と robots.txt を確認してください。
- サーバーに過度な負荷をかけないよう、`FILMY_REQUEST_INTERVAL`（デフォルト5秒）を守ってください。
  この間隔はプロセス内の全 `FilmarksClient` インスタンスで共有され、連続した API コールでも必ず守られます。
- スクレイピング対象サイトの構造変更により、一部エンドポイントが一時的に応答不能になる可能性があります
  （その場合、エラー系ステータスコード 404 / 503 を返します）。
