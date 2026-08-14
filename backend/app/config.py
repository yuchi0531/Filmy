from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定。環境変数で上書き可能。"""

    # Filmarks ベースURL
    filmarks_base_url: str = "https://filmarks.com"

    # HTTPタイムアウト（秒）
    request_timeout: float = 15.0

    # スクレイピング間隔（秒）
    request_interval: float = 5.0

    # キャッシュTTL（秒）
    cache_ttl_movie_list: int = 21600  # 6時間
    cache_ttl_movie_detail: int = 86400  # 24時間
    cache_ttl_schedule: int = 86400  # 24時間（スケジュールは毎週火曜更新のため）
    cache_ttl_theater: int = 86400  # 24時間
    cache_ttl_search: int = 3600  # 1時間

    # ブラウザ風User-Agent
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    # 実行環境（development / production）。
    # production ではAPIキー未設定（api_key=""）を認めず起動時に失敗（fail-closed）させる。
    environment: str = "development"

    # クライアント認証用のAPIキー。
    # - development では空文字なら認証をスキップ（ローカル開発・既存テスト互換）。
    # - production では空文字を許さない（auth.require_api_key が 503 を返す）。
    api_key: str = ""

    # 信頼できるリバースプロキシのIP（カンマ区切り）。
    # ここに列挙されたプロキシ経由のリクエストのみ X-Forwarded-For を信頼する。
    # 未設定（空）なら XFF を一切信頼せず、直結IP（request.client.host）を使う。
    trusted_proxies: str = ""

    # クライアント向けレート制限（IPごとの1分あたり最大リクエスト数）
    rate_limit_per_minute: int = 60

    # 劇場座標の永続キャッシュ（SQLite）のファイルパス
    coord_cache_path: str = "./data/theater_coords.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FILMY_",
        extra="ignore",
    )


settings = Settings()