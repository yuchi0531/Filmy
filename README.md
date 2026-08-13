# Filmy

[Filmarks](https://filmarks.com) の映画・劇場・上映スケジュール情報を提供するモノレポプロジェクト。

- **backend/**: FastAPI 製のスクレイピングAPIサーバー（Filmarks をクロールして JSON を返す）
- **android/**: Android アプリ（Compose + Material 3、バックエンドAPIを利用する前提。未作成）

## モノレポ構造

```
filmy/
├── backend/                  # FastAPI バックエンド
│   ├── app/
│   │   ├── main.py           # FastAPIインスタンス、CORS、ルート登録
│   │   ├── config.py         # pydantic-settings による環境変数設定
│   │   ├── routers/          # APIルーター（movies / theaters / search）
│   │   ├── scrapers/         # Filmarks スクレイピング実装（後で実装）
│   │   ├── models/           # Pydantic レスポンスモデル（後で実装）
│   │   └── cache/            # cachetools によるレスポンスキャッシュ（後で実装）
│   ├── Dockerfile            # python:3.12-slim
│   ├── fly.toml              # Fly.io デプロイ設定
│   └── requirements.txt
└── README.md
```

## セットアップ手順

### バックエンド（ローカル開発）

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

動作確認:

```bash
curl http://localhost:8000/health
# => {"status":"ok"}
```

### 環境変数

設定は `app/config.py` の `Settings` クラスに定義されており、環境変数（プレフィックス `FILMY_`）で上書きできる。

| 環境変数 | デフォルト | 説明 |
| --- | --- | --- |
| `FILMY_FILMARKS_BASE_URL` | `https://filmarks.com` | Filmarks のベースURL |
| `FILMY_REQUEST_TIMEOUT` | `15` | HTTPリクエストのタイムアウト（秒） |
| `FILMY_REQUEST_INTERVAL` | `5` | スクレイピング間隔（秒） |
| `FILMY_CACHE_TTL_MOVIE_LIST` | `21600` | 映画一覧キャッシュTTL（秒・6時間） |
| `FILMY_CACHE_TTL_MOVIE_DETAIL` | `86400` | 映画詳細キャッシュTTL（秒・24時間） |
| `FILMY_CACHE_TTL_SCHEDULE` | `3600` | 上映スケジュールキャッシュTTL（秒・1時間） |
| `FILMY_CACHE_TTL_THEATER` | `86400` | 劇場情報キャッシュTTL（秒・24時間） |
| `FILMY_CACHE_TTL_SEARCH` | `3600` | 検索結果キャッシュTTL（秒・1時間） |
| `FILMY_USER_AGENT` | ブラウザUA | スクレイピング時のUser-Agent |

### Docker ビルド

```bash
cd backend
docker build -t filmy-backend .
docker run -p 8080:8080 filmy-backend
```

### Fly.io デプロイ

```bash
cd backend
fly launch
fly deploy
```

## 免責事項

本プロジェクトは Filmarks のスクレイピングにより情報を取得します。利用時は [Filmarks 利用規約](https://filmarks.com/terms) と robots.txt を確認し、サーバーに過度な負荷をかけないよう `REQUEST_INTERVAL` を守ってください。
