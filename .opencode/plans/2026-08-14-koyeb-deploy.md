# Koyeb 公開計画（自分専用・APIキー認証 + レート制限付き）

## 目的

バックエンド（FastAPI）を Koyeb にデプロイし、外出先の実機からも利用できるようにする。
公開前の必須対策として、現在皆無の **APIキー認証** と **クライアント向けレート制限** を追加する。

## 背景（調査済みの現状）

- バックエンドは **認証なし・クライアント向けレート制限なし・CORS `*`** の状態。
- Filmarks へのスクレイピング間隔（5秒スロットル）は内部向けで、外部からの大量リクエストは無制限。
- 自分専用とはいえ公開すると全世界からアクセス可能になるため、APIキー認証が必須。
- Koyeb は無料枠（512MB/0.1vCPU/2GB、クレカ登録必須）で 24/7 常駐。README にデプロイ手順あり。
- 過去セッションで Fly.io 無料枠廃止を経て **Koyeb に決定済み**（`flyio-hosting-alternatives-2026` メモリ参照）。

## 変更内容

### 1. バックエンド: APIキー認証の追加（依存追加なし・自前実装）

**新規: `backend/app/auth.py`**
- 環境変数 `FILMY_API_KEY`（pydantic-settings の `Settings` に `api_key: str = ""` を追加）を読み取る。
- FastAPI の `Depends` で使う関数 `require_api_key` を提供:
  - リクエストヘッダー `X-API-Key` を検証。
  - `FILMY_API_KEY` が空文字（未設定）の場合:
    - **ローカル開発時**は認証をスキップ（後方互換。既存テストを壊さない）。
    - **本番（Koyeb）では必ず設定する**ことを README に明記。
  - 不一致なら `HTTPException(401, "invalid or missing API key")`。
- 比較は `hmac.compare_digest`（タイミング攻撃対策）を使用。

**変更: `backend/app/main.py`**
- ルーター登録時に `dependencies=[Depends(require_api_key)]` を付与（`/health` は認証除外のまま＝Koyeb ヘルスチェック用）。

**変更: `backend/app/config.py`**
- `api_key: str = ""` を追加。

### 2. バックエンド: クライアント向けレート制限の追加（依存追加なし・簡易実装）

**新規: `backend/app/rate_limit.py`**
- インメモリの簡易レートリミッター（IP ごと）:
  - `collections.defaultdict` + `time.monotonic` で IP ごとのアクセス時刻を記録。
  - 制限値は環境変数 `FILMY_RATE_LIMIT`（例: 60 req/min）で設定可能。
  - 超過時は `HTTPException(429, "too many requests")`。
- 実装は `require_api_key` と同様に `Depends` で使える関数 `rate_limit` を提供。
- スレッドセーフ（`threading.Lock`）にする。
- プロセスが再起動するとカウンタはリセットされるが、自分専用用途では十分（KISS）。本格的な制御が必要なら `slowapi` への差し替えを将来検討、と README に注記。

**変更: `backend/app/main.py`**
- `rate_limit` も `dependencies=[...]` に追加。

### 3. Android: APIキーをヘッダーに付与

**変更: `app/src/main/java/com/filmy/app/data/api/ApiClient.kt`**
- OkHttp の `Interceptor` を追加し、全リクエストに `X-API-Key` ヘッダーを付与。
- APIキーは `BuildConfig.API_KEY` から取得（下記 build.gradle.kts で定義）。
- キーは release/debug 両方で同じ Koyeb のキーを使う想定。

**変更: `app/build.gradle.kts`**
- `buildConfigField("String", "API_KEY", "\"<実際のキー>\")` を release / debug 両方に追加。
- ※ キーをソースに埋め込むため、完全秘匿はできない（難読化しても限界）。自分専用用途の「無差別アクセス抑制」と割り切る。README に明記。

### 4. Android: release の API_BASE_URL を Koyeb URL に変更

**変更: `app/build.gradle.kts`**
- release の `API_BASE_URL` を現在の仮値 `https://filmy.koyeb.app/` から **実際にデプロイした Koyeb URL** に変更。
- ※ 正確な URL は Koyeb デプロイ後に確定するため、デプロイ手順の後で埋める（プレースホルダーでもよいが、最終確定は必須）。

### 5. Koyeb デプロイ（手順）

- `backend/koyeb.yaml`（既存）を確認。なければ作成。
- 環境変数（Koyeb secret）に `FILMY_API_KEY` を設定（必須）。
- Koyeb CLI でデプロイ:
  ```bash
  cd backend
  koyeb app create filmy
  koyeb service create filmy --docker . --port 8080 --env FILMY_API_KEY=<キー>
  ```
- デプロイ後、`curl -H "X-API-Key: <キー>" https://<koyeb-url>/health` で疎通確認。

## 実装順序

1. バックエンド: `config.py`（api_key 追加）→ `auth.py`（認証）→ `rate_limit.py`（レート制限）→ `main.py`（dependencies 付与）
2. バックエンド: テスト追加（認証あり/なし、レート制限超過）→ 全テストパス確認
3. Android: `build.gradle.kts`（API_KEY 追加、release URL 変更）→ `ApiClient.kt`（Interceptor 追加）
4. Android: `assembleDebug` ビルド確認（debug は既存 `http://127.0.0.1:8000/` のまま）
5. Koyeb デプロイ → 疎通確認 → release URL 確定

## 検証方法

- **バックエンド単体**: `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`（既存123件 + 認証/レート制限の新テスト）
- **認証動作**: `curl -H "X-API-Key: <キー>" http://localhost:8000/api/movies/now` が 200、キー無しが 401
- **レート制限**: 制限超過で 429
- **Android ビルド**: `gradle :app:assembleDebug`
- **E2E（デプロイ後）**: 実機で設定画面から Koyeb URL + APIキーを設定し、Home 画面でデータ取得

## リスク・注意点

- **APIキーのソース埋め込みは完全秘匿不可**。自分専用用途と割り切る。漏れたら Koyeb 側でキーをローテーションする運用。
- **Filmarks へのアクセスは Koyeb の IP から飛ぶ**（自宅 IP がブロックされるリスクなし）。5秒スロットルは引き続き守る。
- レート制限はインメモリ実装のため、Koyeb のスケール（複数コンテナ）時は機能しない。無料枠（1コンテナ）なら問題なし。
- Koyeb 無料枠はクレカ登録が必須。
