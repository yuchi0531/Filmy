"""テスト用のフェイク Filmarks クライアント。

``get_html`` がモック HTML/JSON を返すだけで、実際のネットワークには
一切アクセスしない。スクレイパー単体テストで使用する。
"""

from __future__ import annotations

from tests import mock_html


class FakeFilmarksClient:
    """``get_html(path)`` が実体を返すフェイク。

    paths に該当しない場合は、``/pia_theaters/...``（劇場スケジュールJSON）に
    応答する。それ以外は AssertionError を投げて意図しないネットワーク依存的
    パスを検出する。
    """

    def __init__(self, pages=None) -> None:
        self.pages = dict(pages or {})
        self.calls: list[str] = []

    def get_html(self, path: str) -> str:
        self.calls.append(path)
        if path in self.pages:
            return self.pages[path]
        if path.startswith("/pia_theaters/"):
            # 日付別スケジュールJSON: 任意の schedule_date に応答
            return mock_html.SCHEDULE_JSON
        raise AssertionError(f"予期しないパスがリクエストされました: {path!r}")

    def get_html_batch(self, paths: list[str]) -> list[str | None]:
        return [self._respond(path) for path in paths]

    def _respond(self, path: str) -> str | None:
        self.calls.append(path)
        if path in self.pages:
            return self.pages[path]
        if path.startswith("/pia_theaters/"):
            return mock_html.SCHEDULE_JSON
        return None

    def close(self) -> None:
        pass

    def __enter__(self) -> "FakeFilmarksClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()