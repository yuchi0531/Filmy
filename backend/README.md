# Filmy Backend

Filmarks の映画情報を提供する FastAPI 製スクレイピングAPI。

## 起動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## エンドポイント

### ヘルスチェック

- `GET /health` — `{"status": "ok"}`

### 映画一覧（ページング対応）

- `GET /api/movies/now` — 上映中の映画一覧
- `GET /api/movies/coming` — 公開予定の映画一覧
- `GET /api/movies/upcoming` — 今週公開の映画一覧
- `GET /api/movies/trend` — トレンドの映画一覧

すべて `?page=N`（1始まり、デフォルト1）でページング可能。レスポンスに
`page` と `has_next`（次ページの有無）を含む。

### 映画検索

- `GET /api/search?q=ドラえもん` — 映画検索。`q` は1〜200文字。
  `?page=N` でページング可能（レスポンスは一覧と共通形式）。

### 映画詳細

- `GET /api/movies/{movie_id}` — 映画詳細（movie_id は数字のみ）。

### 劇場（theaters）

- `GET /api/theaters/{prefecture}` — 都道府県のエリア一覧
  （例: `/api/theaters/tokyo`。prefecture は Filmarks の slug 例: `tokyo`）
- `GET /api/theaters/{prefecture}/{area_id}` — エリアの劇場一覧
  （例: `/api/theaters/tokyo/99`。area_id は数字のみ）
- `GET /api/theaters/{prefecture}/{area_id}/{theater_id}` — 劇場詳細＋上映スケジュール
  （例: `/api/theaters/tokyo/99/16`。スケジュールは今日から7日分を映画別に集約）
- `GET /api/theaters/nearby?lat=..&lng=..&radius=10` — 近隣劇場検索
  （radius は1〜100km、デフォルト10。Filmarks の `/pia_theaters` JSON API の半径フィルタ・距離順を利用）

注意: 劇場の緯度経度は Filmarks 側に存在しないため、詳細の `latitude`/`longitude` は
`null`、近隣の `distance_km` は未設定。近隣は Filmarks サーバ側での距離順をそのまま返す。

### レスポンス形式（一覧・検索共通）

```json
{
  "query": null,
  "heading": "上映中の最新映画おすすめ人気ランキング 459作品",
  "results": [
    {
      "id": "119606",
      "title": "...",
      "rating": 3.8,
      "poster_url": "https://...",
      "release_date": "2026年07月31日",
      "genres": ["ドラマ", "コメディ"],
      "mark_count": 1200,
      "clip_count": 45
    }
  ],
  "total": 459,
  "page": 1,
  "has_next": true
}
```

### キャッシュ

- 一覧・検索はページごとにキャッシュ（`GET /api/movies/now?page=1` と
  `?page=2` は別キャッシュ）。TTLは環境変数で変更可能（デフォルトは
  一覧6時間 / 詳細24時間 / 検索1時間）。

- 劇場系は 都道府県/エリア一覧 24時間、劇場詳細＋スケジュール 1時間、
  近隣検索 1時間のキャッシュ。

## 構造

```
app/
├── main.py        # FastAPIインスタンス、CORS、ルート登録
├── config.py      # pydantic-settings による設定（FILMY_ プレフィックス）
├── routers/       # APIルーター（movies / theaters / search / common）
├── scrapers/      # Filmarks スクレイピング実装
│   ├── http_client.py  # FilmarksClient（プロセス共有のリクエスト間隔制御）
│   ├── parser.py       # エラーページ検出・安全な数値変換などの共通ヘルパー
│   ├── list_scraper.py # 一覧スクレイパー（検索スクレイパーと共有のカードパーサ）
│   ├── search_scraper.py
│   ├── movie_scraper.py
│   ├── theater_scraper.py # 劇場リスト/詳細+スケジュールスクレイパー
│   ├── geo.py             # 距離計算ユーティリティ（haversine）
│   └── base.py / exceptions.py
├── models/        # Pydantic レスポンスモデル
└── cache/         # cachetools による名前空間別 TTL キャッシュ
```

## デプロイ

- **Docker**: `python:3.12-slim` ベース、ポート 8080
- **Fly.io**: `fly.toml`（shared-cpu-1x / 256MB、ヘルスチェック `GET /health`）

## 免責事項

Filmarks の利用規約と robots.txt を確認し、`FILMY_REQUEST_INTERVAL`（デフォルト5秒）を
守って利用すること。リクエスト間隔はプロセス内のすべての `FilmarksClient` インスタンスで
共有され、連続した API コールでも Filmarks へのアクセス間隔が保証される。
