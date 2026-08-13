"""スクレイピング関連のカスタム例外。"""


class FilmarksError(Exception):
    """Filmarks スクレイピングの基底例外。"""


class FilmarksUnavailableError(FilmarksError):
    """Filmarks が一時的にアクセスできない状態。"""


class FilmarksNotFoundError(FilmarksError):
    """対象ページが見つからない。"""


class FilmarksParseError(FilmarksError):
    """HTML パースに失敗。"""
