# Filmy Backend

Filmarks の映画・劇場・上映スケジュール情報を提供する **FastAPI 製スクレイピングAPI**。

- 実際の Filmarks にはアクセスするが、アクセス間隔をプロセス共有で5秒に制限し、
  結果をインメモリキャッシュして負荷を軽減する。
- スクレイピングは `app/scrapers/` に、レスポンスモデルは `app/models/` に分離。
- 例外は `app/routers/common.py` の `run_scrape` で HTTP ステータスコードに変換。

## 要件

- Python 3.12+（pydantic v2 / pydantic-settings 対応）
- 依存パッケージは `requirements.txt` に列挙

## 起動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 開発サーバー（REST API）
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

ヘルスチェック:

```bash
curl http://localhost:8000/health
# => {"status":"ok"}
```

## APIエンドポイント

フルリファレンス（パラメータ・レスポンス例・エラーコード）は [API.md](API.md) を参照。

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/health` | ヘルスチェック |
| GET | `/api/movies/now` | 上映中の映画一覧 |
| GET | `/api/movies/coming` | 公開予定の映画一覧 |
| GET | `/api/movies/upcoming` | 今週公開の映画一覧 |
| GET | `/api/movies/trend` | トレンドの映画一覧 |
| GET | `/api/movies/{movie_id}` | 映画詳細（movie_id=数字のみ） |
| GET | `/api/search?q=&page=` | 映画検索 |
| GET | `/api/theaters/{prefecture}` | 都道府県のエリア一覧 |
| GET | `/api/theaters/{prefecture}/{area_id}` | エリアの劇場一覧 |
| GET | `/api/theaters/{prefecture}/{area_id}/{theater_id}` | 劇場詳細＋上映スケジュール |
| GET | `/api/theaters/nearby?lat=&lng=&radius=` | 近隣劇場検索 |

## キャッシュ戦略

`cachetools.TTLCache` によるインメモリキャッシュ（`app/cache/__init__.py`、名前空間別・スレッドセーフ）。

| 対象 | 名前空間 | デフォルトTTL | 環境変数 |
| --- | --- | --- | --- |
| 映画一覧（now/coming/upcoming/trend、ページ別） | `movie_list` | 6時間 (21600s) | `FILMY_CACHE_TTL_MOVIE_LIST` |
| 映画詳細 | `movie_detail` | 24時間 (86400s) | `FILMY_CACHE_TTL_MOVIE_DETAIL` |
| 劇場詳細＋スケジュール | `theater_detail` | 1時間 (3600s) | スケジュール用 TTL |
| 都道府県・エリア一覧 | `theater_pref` / `theater_area` | 24時間 (86400s) | `FILMY_CACHE_TTL_THEATER` |
| 近隣検索 | `theater_nearby` | 1時間 (3600s) | スケジュール用 TTL |
| 検索結果（`q:page` 別） | `search` | 1時間 (3600s) | `FILMY_CACHE_TTL_SEARCH` |

- 一覧・検索は **ページごとにキャッシュキーを分離**（`now:1` と `now:2` は別キャッシュ）。
- キャッシュの最大エントリ数は名前空間あたり 256（`CACHE_MAXSIZE`）。

### スクレイピング間隔（スロットル）

- `FilmarksClient` は**プロセス共有されたロック＋タイムスタンプ**でアクセス間隔を制御。
  全インスタンスが同じ間隔（デフォルト5秒）を守る。
- テストでは `FILMY_REQUEST_INTERVAL=0` に設定して高速化する（`tests/conftest.py`）。

## テスト実行方法

121件のテスト（単体99件 + 結合22件）を実行:

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

テストは **実ネットワークに一切アクセスしません**。

- `tests/` — 単体テスト（モデル・パーサー・スクレイパー・HTTPクライアント・キャッシュ・ルーター）
- `tests/test_integration.py` — **結合テスト**。全APIエンドポイントを
  `TestClient` 経由で一気通貫に検証（FastAPI → ルーター → スクレイパー → パーサー）。
  ネットワーク層だけを `tests/fake_client.py` の `FakeFilmarksClient`（モッククライアント）に差し替え。
- `tests/conftest.py` — 共通フィクスチャ（ベースURLを到達不能ドメイン化、スロットル0、キャッシュクリア）

## 構造

```
app/
├── main.py            # FastAPIインスタンス、CORS（全オリジン）、ルート登録
├── config.py          # pydantic-settings（FILMY_ プレフィックス）
├── routers/
│   ├── common.py      # run_scrape（スクレイピング例外 → HTTP 変換）
│   ├── movies.py      # /api/movies/*
│   ├── search.py      # /api/search
│   └── theaters.py    # /api/theaters/*
├── scrapers/
│   ├── http_client.py # FilmarksClient（プロセス共有スロットル、例外変換）
│   ├── parser.py      # エラーページ検出・安全な数値変換
│   ├── base.py        # BaseScraper（HTML取得→パース→エラー検出）
│   ├── list_scraper.py
│   ├── search_scraper.py
│   ├── movie_scraper.py
│   ├── theater_scraper.py
│   └── exceptions.py  # FilmarksError系
├── models/            # Pydantic レスポンスモデル
└── cache/             # CacheManager（TTLCache、名前空間別）
```

## 環境変数

設定は `app/config.py` の `Settings` に定義。環境変数（`FILMY_` プレフィックス）で上書き可能。

| 環境変数 | デフォルト | 説明 |
| --- | --- | --- |
| `FILMY_FILMARKS_BASE_URL` | `https://filmarks.com` | Filmarks のベースURL |
| `FILMY_REQUEST_TIMEOUT` | `15` | HTTPリクエストのタイムアウト（秒） |
| `FILMY_REQUEST_INTERVAL` | `5` | スクレイピング間隔（秒・プロセス共有） |
| `FILMY_CACHE_TTL_MOVIE_LIST` | `21600` | 映画一覧キャッシュTTL（6時間） |
| `FILMY_CACHE_TTL_MOVIE_DETAIL` | `86400` | 映画詳細キャッシュTTL（24時間） |
| `FILMY_CACHE_TTL_SCHEDULE` | `3600` | スケジュールキャッシュTTL（1時間） |
| `FILMY_CACHE_TTL_THEATER` | `86400` | 劇場情報キャッシュTTL（24時間） |
| `FILMY_CACHE_TTL_SEARCH` | `3600` | 検索キャッシュTTL（1時間） |
| `FILMY_USER_AGENT` | ブラウザUA | スクレイピング時のUser-Agent |
| `FILMY_ENVIRONMENT` | `development` | 実行環境（`development` / `production`） |
| `FILMY_API_KEY` | （空文字） | クライアント認証用APIキー（developmentでは空なら認証無効、productionでは空なら503） |
| `FILMY_TRUSTED_PROXIES` | （空文字） | 信頼できるリバースプロキシのIP（カンマ区切り）。未設定ならX-Forwarded-Forを信頼しない |
| `FILMY_RATE_LIMIT_PER_MINUTE` | `60` | クライアント向けレート制限（IPごと・1分あたり、0以下で無効） |

## Koyeb デプロイ

Docker コンテナとして Koyeb（無料常駐インスタンス）にデプロイします。

### ローカルで Docker イメージを確認

```bash
cd backend
docker build -t filmy-backend .
docker run -p 8080:8080 filmy-backend
curl http://localhost:8080/health
# => {"status":"ok"}
```

### Koyeb CLI でデプロイ

```bash
curl -fsSL https://raw.githubusercontent.com/koyeb/cli/master/install.sh | sh
koyeb login

cd backend
koyeb app create filmy
koyeb service create filmy --docker . --port 8080
```

### APIキー認証の設定（必須）

公開前に必ず `FILMY_API_KEY` を設定してください。`FILMY_ENVIRONMENT=production` のときに
`FILMY_API_KEY` が未設定（空）だと、認証をスキップせず **503（fail-closed）** を返して
エンドポイントを公開しません（設定漏れによる全世界公開を防止）。

```bash
koyeb secret create FILMY_API_KEY=<強力なランダムキー>
# production 環境であることを明示（省略時は development となり認証がスキップされる）
koyeb secret create FILMY_ENVIRONMENT=production
# サービスにシークレットを割り当て（必要に応じて再デプロイ）
koyeb service update filmy --env FILMY_API_KEY=@FILMY_API_KEY --env FILMY_ENVIRONMENT=@FILMY_ENVIRONMENT
```

任意でレート制限も調整できます:

```bash
koyeb secret create FILMY_RATE_LIMIT_PER_MINUTE=60
```

Koyeb 等のリバースプロキシ越しに正しくクライアントIPでレート制限したい場合は、
プロキシのIPを `FILMY_TRUSTED_PROXIES`（カンマ区切り）に設定してください。
未設定のままでも、X-Forwarded-For を信頼せず直結IPでレート制限するため
（スプーフィング対策）、動作自体は安全です。

デプロイ後の疎通確認:

```bash
curl -H "X-API-Key: <キー>" https://<公開URL>/api/movies/now
# キーなしだと 401 が返る
curl https://<公開URL>/api/movies/now
```

> 注意: `FILMY_ENVIRONMENT=production` の場合は `FILMY_API_KEY` が必須です。
> 未設定のままだと 503 でリクエストを拒否します（fail-closed）。
> `development`（デフォルト）では空キーで認証をスキップするため、公開環境では
> 必ず `production` を設定してください。

- ポート `8080`（Dockerfile の `EXPOSE 8080`、`CMD uvicorn ... --port 8080`）
- ヘルスチェック: `GET /health`（Dockerfile の `HEALTHCHECK` と Koyeb の両方で確認）
- 環境変数: `koyeb secret create FILMY_XXX=...` で設定し、サービスに割り当てる
- デプロイ設定の参考: [`koyeb.yaml`](koyeb.yaml)（ポート 8080・無料常駐インスタンス・/health チェック）

参考: [フロントの README（ルート）](../README.md)

## 免責事項

Filmarks の利用規約と robots.txt を確認し、`FILMY_REQUEST_INTERVAL`（デフォルト5秒）を
守って利用すること。リクエスト間隔はプロセス内のすべての `FilmarksClient` インスタンスで
共有され、連続した API コールでも Filmarks へのアクセス間隔が保証される。