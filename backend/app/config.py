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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FILMY_",
        extra="ignore",
    )


settings = Settings()