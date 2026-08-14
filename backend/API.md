# Filmy Backend APIドキュメント

Filmarks の映画・劇場・上映スケジュール情報を提供する REST API のリファレンス。

- ベースURL: `http://localhost:8000`（本番は Koyeb の公開URL）
- 全エンドポイント: `GET`
- レスポンス形式: JSON（UTF-8 / snake_case）
- APIドキュメント（Swagger UI）: `GET /docs`

## 共通仕様

### クエリパラメータ

| パラメータ | 型 | 制約 | 説明 |
| --- | --- | --- | --- |
| `page` | int | `>= 1`（デフォルト1） | ページ番号（一覧・検索のみ） |
| `q` | str | 1〜200文字 | 検索キーワード（検索のみ） |

### エラーコード

| HTTP | 意味 | 例 |
| --- | --- | --- |
| `200` | 成功 | — |
| `404` | リソースが見つからない | 存在しない映画ID・ Filmarksの404相当ページ |
| `422` | バリデーションエラー（パラメータ不正） | 数字でない movie_id、空の q、radius 範囲外 |
| `503` | Filmarks が一時的に利用不能 | タイムアウト・403/429/5xx、アクセス不可ページ |
| `500` | サーバー内部エラー（パース失敗等） | Filmarks の構文変更によるパース失敗 |

エラー時のレスポンスボディ（FastAPI 標準）:

```json
{ "detail": "エラー内容" }
```

## エンドポイント一覧

| メソッド | パス | 説明 |
| --- | --- | --- |
| GET | `/health` | ヘルスチェック |
| GET | `/api/movies/now` | 上映中の映画一覧 |
| GET | `/api/movies/coming` | 公開予定の映画一覧 |
| GET | `/api/movies/upcoming` | 今週公開の映画一覧 |
| GET | `/api/movies/trend` | トレンドの映画一覧 |
| GET | `/api/movies/{movie_id}` | 映画詳細 |
| GET | `/api/search` | 映画検索 |
| GET | `/api/theaters/{prefecture}` | 都道府県のエリア一覧 |
| GET | `/api/theaters/{prefecture}/{area_id}` | エリアの劇場一覧 |
| GET | `/api/theaters/{prefecture}/{area_id}/{theater_id}` | 劇場詳細＋上映スケジュール |
| GET | `/api/theaters/nearby` | 近隣劇場検索 |

---

## 1. ヘルスチェック

`GET /health`

レスポンス例:

```json
{ "status": "ok" }
```

---

## 2. 映画一覧（上映中 / 公開予定 / 今週公開 / トレンド）

`GET /api/movies/now`
`GET /api/movies/coming`
`GET /api/movies/upcoming`
`GET /api/movies/trend`

クエリパラメータ:

| パラメータ | 必須 | デフォルト | 制約 |
| --- | --- | --- | --- |
| `page` | 任意 | 1 | `>= 1`（1ページ36件） |

レスポンス例（`GET /api/movies/now?page=1`）:

```json
{
  "query": null,
  "heading": "上映中の最新映画 459作品",
  "results": [
    {
      "id": "119606",
      "title": "映画タイトル",
      "original_title": null,
      "rating": 3.8,
      "review_count": null,
      "poster_url": "https://.../poster.jpg",
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

フィールド:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `query` | string/nil | 検索クエリ（一覧では常に null） |
| `heading` | string | ページ見出し |
| `results` | array | 映画サマリーの配列 |
| `total` | int | 総作品数 |
| `page` | int | 現在のページ |
| `has_next` | bool | 次ページの有無 |

`results[]` の要素:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `id` | string | 映画ID（Filmarks movie_id） |
| `title` | string | タイトル |
| `original_title` | string/nil | 原題 |
| `rating` | float/nil | 評価（取得不可の場合は null） |
| `review_count` | int/nil | レビュー数 |
| `poster_url` | string/nil | ポスター画像URL |
| `release_date` | string/nil | 公開日（例 `2026年08月01日`） |
| `genres` | array(string) | ジャンル |
| `mark_count` | int/nil | Mark数 |
| `clip_count` | int/nil | Clip数 |

### キャッシュ

ページごとに別キャッシュ（`now:1` と `now:2` は別）。デフォルトTTL 6時間。

---

## 3. 映画詳細

`GET /api/movies/{movie_id}`

パスパラメータ:

| パラメータ | 型 | 制約 |
| --- | --- | --- |
| `movie_id` | string | 数字のみ（`^\d+$`） |

レスポンス例（`GET /api/movies/119606`）:

```json
{
  "id": "119606",
  "title": "映画タイトル",
  "original_title": "MOVIE TITLE",
  "rating": 3.8,
  "review_count": 42,
  "poster_url": "https://.../poster.jpg",
  "release_date": "2026年07月31日",
  "genres": ["ドラマ", "SF"],
  "mark_count": 1200,
  "clip_count": 45,
  "synopsis": "あらすじ文...",
  "runtime": "120分",
  "director": ["監督名"],
  "cast": [
    { "name": "俳優名", "character": "役名" }
  ],
  "official_site": "https://...",
  "streaming": [
    { "service": "U-NEXT", "type": "見放題" }
  ]
}
```

`cast[]` の要素:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `name` | string | 出演者名 |
| `character` | string/nil | 役名（無い場合は null） |

`streaming[]` の要素:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `service` | string | 配信サービス名 |
| `type` | string | 見放題 / レンタル / 購入 等 |

エラー: 存在しない ID は `404`、数字でない ID は `422`。

キャッシュ: デフォルトTTL 24時間。

---

## 4. 映画検索

`GET /api/search?q={query}`

クエリパラメータ:

| パラメータ | 必須 | 制約 |
| --- | --- | --- |
| `q` | 必須 | 1〜200文字 |
| `page` | 任意 | `>= 1` |

レスポンス例（`GET /api/search?q=ドラえもん`）:

```json
{
  "query": "ドラえもん",
  "heading": "テストに関する映画 3作品",
  "results": [
    {
      "id": "2001",
      "title": "検索結果映画",
      "rating": 4.0,
      "poster_url": "https://...jpg",
      "release_date": "2026年09月01日",
      "genres": ["ドラマ", "SF"],
      "mark_count": 99,
      "clip_count": 7
    }
  ],
  "total": 3,
  "page": 1,
  "has_next": false
}
```

レスポンス形式は映画一覧と共通（`query` のみ検索キーワードが入る）。

エラー: 空の`q` や 200文字超は `422`。

キャッシュ: `q:page` 単位で別キャッシュ。デフォルトTTL 1時間。

---

## 5. 都道府県のエリア一覧

`GET /api/theaters/{prefecture}`

パスパラメータ:

| パラメータ | 型 | 説明 |
| --- | --- | --- |
| `prefecture` | string | Filmarks の都道府県 slug（例: `tokyo`） |

レスポンス例（`GET /api/theaters/tokyo`）:

```json
{
  "prefecture": "東京都",
  "results": [
    {
      "id": "99",
      "name": "新宿",
      "theater_count": 4,
      "url": "/theaters/tokyo/99"
    }
  ],
  "total": 2
}
```

フィールド:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `prefecture` | string | 都道府県名 |
| `results[]` | array | エリア一覧 |
| `total` | int | エリア数 |

`results[]` の要素（AreaSummary）:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `id` | string | エリアID（area_id） |
| `name` | string | エリア名 |
| `theater_count` | int/nil | 劇場数（エリア名から抽出） |
| `url` | string | Filmarks のエリアURL（例 `/theaters/tokyo/99`） |

キャッシュ: デフォルトTTL 24時間。

---

## 6. エリアの劇場一覧

`GET /api/theaters/{prefecture}/{area_id}`

パスパラメータ:

| パラメータ | 型 | 制約 |
| --- | --- | --- |
| `prefecture` | string | 都道府県 slug |
| `area_id` | string | 数字のみ |

レスポンス例（`GET /api/theaters/tokyo/99`）:

```json
{
  "prefecture": "東京都",
  "results": [
    {
      "id": "172",
      "name": "テストシネマ新宿",
      "address": null,
      "prefecture": "東京都",
      "area_id": "99",
      "url": "/theaters/tokyo/99/172",
      "distance_km": null
    }
  ],
  "total": 2
}
```

`results[]` の要素（TheaterSummary）:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `id` | string | 劇場ID |
| `name` | string | 劇場名 |
| `address` | string/nil | 住所 |
| `prefecture` | string | 都道府県名 |
| `area_id` | string/nil | エリアID |
| `url` | string/nil | Filmarks の劇場URL |
| `distance_km` | float/nil | 距離（近隣検索時のみ） |

キャッシュ: デフォルトTTL 24時間。

---

## 7. 劇場詳細＋上映スケジュール

`GET /api/theaters/{prefecture}/{area_id}/{theater_id}`

パスパラメータ:

| パラメータ | 型 | 制約 |
| --- | --- | --- |
| `prefecture` | string | 都道府県 slug |
| `area_id` | string | 数字のみ |
| `theater_id` | string | 数字のみ |

レスポンス例（`GET /api/theaters/tokyo/99/172`）:

```json
{
  "id": "172",
  "name": "テストシネマ新宿",
  "address": "東京都新宿区新宿3-1-1",
  "prefecture": "東京都",
  "area_id": "99",
  "url": "/theaters/tokyo/99/172",
  "distance_km": null,
  "latitude": null,
  "longitude": null,
  "map_url": "https://maps.google.com/?q=テストシネマ新宿",
  "movies": [
    {
      "movie_id": "3001",
      "movie_title": "スケジュール映画",
      "poster_url": "https://...jpg",
      "dates": {
        "2026-08-14": ["10:00", "13:30"],
        "2026-08-15": ["10:00", "13:30"]
      }
    }
  ]
}
```

`movies[]` の要素（MovieSchedule）:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `movie_id` | string | 映画ID |
| `movie_title` | string | 映画タイトル |
| `poster_url` | string/nil | ポスター画像URL |
| `dates` | object | `{"YYYY-MM-DD": ["HH:MM", ...]}` の上映時刻マップ |

注意:

- 劇場の緯度経度は Filmarks 側に存在しないため、`latitude` / `longitude` は null。
- スケジュールは **今日から3日分** を映画別に集約（`schedule_days=3`）。

キャッシュ: デフォルトTTL 1時間（スケジュールは鮮度が重要）。

---

## 8. 近隣劇場検索

`GET /api/theaters/nearby?lat={lat}&lng={lng}&radius={radius}`

クエリパラメータ:

| パラメータ | 必須 | デフォルト | 制約 |
| --- | --- | --- | --- |
| `lat` | 必須 | — | 緯度（float） |
| `lng` | 必須 | — | 経度（float） |
| `radius` | 任意 | 10.0 | 1〜100（km） |

レスポンス例（`GET /api/theaters/nearby?lat=35.0&lng=139.0&radius=10`）:

```json
{
  "latitude": 35.0,
  "longitude": 139.0,
  "radius_km": 10.0,
  "theaters": [
    {
      "id": "172",
      "name": "テストシネマ新宿",
      "address": null,
      "prefecture": "近隣",
      "area_id": "99",
      "url": "/theaters/tokyo/99/172",
      "distance_km": null
    }
  ]
}
```

フィールド:

| フィールド | 型 | 説明 |
| --- | --- | --- |
| `latitude` | float | 指定した緯度 |
| `longitude` | float | 指定した経度 |
| `radius_km` | float | 検索半径（km） |
| `theaters` | array | 近隣劇場一覧（TheaterSummary） |

注意:

- 近隣検索は Filmarks の `/pia_theaters` JSON API の**半径フィルタ・距離順**を利用する。
  座標が外部に公開されていないため `distance_km` は未設定（null）。
- `lat` / `lng` 省略、または `radius` が 1〜100 範囲外は `422`。

キャッシュ: 位置情報ベースのため鮮度重視。デフォルトTTL 1時間。

---

## キャッシュ戦略（まとめ）

| エンドポイント | TTL | キャッシュキー |
| --- | --- | --- |
| 映画一覧 | 6時間 | `endpoint:page` |
| 映画詳細 | 24時間 | `movie_id` |
| 検索 | 1時間 | `q:page` |
| 都道府県・エリア一覧 | 24時間 | `prefecture` / `prefecture:area_id` |
| 劇場詳細＋スケジュール | 1時間 | `theater_id` |
| 近隣検索 | 1時間 | `lat:lng:radius` |

TTL・キャッシュ最大サイズ（名前空間あたり 256）は環境変数で変更可能。
詳細は [backend/README.md](README.md) を参照。