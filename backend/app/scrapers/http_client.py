"""Filmarks スクレイピング用 HTTP クライアント。"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import httpx

from app.config import settings
from app.scrapers.exceptions import (
    FilmarksError,
    FilmarksNotFoundError,
    FilmarksUnavailableError,
)

# ステータスコードによるエラー分類
# 401/403/429 はアクセス不可、5xx は一時的なサーバー障害として Unavailable に分類する
_STATUS_UNAVAILABLE = {401, 403, 429, 500, 502, 503, 504}


# リクエスト間隔制御（モジュール/プロセス共有）。
# インスタンスごとではなく、すべての FilmarksClient が同じロックとタイムスタンプを
# 共有することで、連続した API コールでも Filmarks へのアクセス間隔が必ず守られる。
# 間隔は起動時に settings.request_interval（既定5秒）から決定され、以降は固定。
# コンストラクタ引数では変更できない（テストは monkeypatch で無効化する）。
_throttle_lock = threading.Lock()
_throttle_interval: float = settings.request_interval
# 初回リクエストは待機しないよう「前回 = 現在 - interval」で初期化
_last_request_at: float = time.monotonic() - settings.request_interval


def _wait_interval() -> None:
    """前回の（プロセス共有）リクエストから一定間隔経過するまで待機する。

    ロックを保持したまま待機・更新するため、複数スレッドが同時に呼んでも
    リクエスト間隔が直列化されて必ず守られる。
    """
    global _last_request_at
    with _throttle_lock:
        wait = _throttle_interval - (time.monotonic() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


class FilmarksClient:
    """Filmarks への HTTP リクエストを管理するクライアント。

    - ブラウザ風のデフォルトヘッダーを付与
    - リクエスト間隔（REQUEST_INTERVAL）をプロセス共有でスレッドセーフに保証
    - タイムアウト・ステータスコードエラーを専用例外に変換
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.filmarks_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.request_timeout

        default_headers = {
            "Referer": f"{self.base_url}/",
            "User-Agent": settings.user_agent,
            "Accept-Language": "ja,en;q=0.9",
        }
        if headers:
            default_headers.update(headers)

        self._client = httpx.Client(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            headers=default_headers,
            transport=transport,
        )

    def get_html(self, path: str) -> str:
        """フルURLまたはパスを受け取り、HTML文字列を返す。

        リクエスト間隔を守り、タイムアウト・ステータスコードエラーは例外に変換する。
        """
        url = urljoin(f"{self.base_url}/", path)
        _wait_interval()
        try:
            response = self._client.get(url)
        # TimeoutException / TransportError / TooManyRedirects / DecodingError を
        # 親クラスの RequestError でまとめて捕捉し、Unavailable に変換する
        except httpx.RequestError as exc:
            if isinstance(exc, httpx.TimeoutException):
                raise FilmarksUnavailableError(f"タイムアウト: {url}") from exc
            raise FilmarksUnavailableError(f"通信エラー: {url} ({exc})") from exc
        self._raise_for_status(response)
        return response.text

    def get_html_batch(self, paths: list[str]) -> list[str | None]:
        """複数のパスを並列に取得し、各結果（失敗は None）を入力順で返す。

        「劇場詳細1件 = 1論理操作」とみなし、バッチ全体の前にスロットルを1回だけ
        適用する。バッチ内は並列で投げ、個々の失敗は例外を投げずに None を返す。
        バッチ終了後は `_last_request_at` を更新し、次のバッチ/リクエストが
        再び interval 分待つようにする。
        """
        if not paths:
            return []
        _wait_interval()  # バッチ全体の前に1回スロットル

        def _fetch_one(path: str) -> str | None:
            url = urljoin(f"{self.base_url}/", path)
            try:
                response = self._client.get(url)
            except httpx.RequestError:
                return None
            try:
                self._raise_for_status(response)
            except FilmarksError:
                return None
            return response.text

        # Filmarks への同時接続数を制限し、バーストアクセス（過剰負荷）を防ぐ。
        # paths の件数分だけ並列に投げると、5秒スロットルの意図が骨抜きになるため
        # 同時実行ワーカー数を最大5に制限する。
        max_workers = min(len(paths), 5)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(_fetch_one, paths))

        global _last_request_at
        with _throttle_lock:
            _last_request_at = time.monotonic()
        return results

    def _raise_for_status(self, response: httpx.Response) -> None:
        """ステータスコードを検査し、エラーを例外に変換する。"""
        if response.status_code == 200:
            return
        if response.status_code == 404:
            raise FilmarksNotFoundError(f"ページが見つかりません (404): {response.url}")
        if response.status_code in _STATUS_UNAVAILABLE:
            raise FilmarksUnavailableError(
                f"Filmarks が一時的に利用できません ({response.status_code}): {response.url}"
            )
        raise FilmarksError(
            f"予期しないステータスコード {response.status_code}: {response.url}"
        )

    def close(self) -> None:
        """基盤の httpx.Client をクローズする。"""
        self._client.close()

    def __enter__(self) -> "FilmarksClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
