"""app/scrapers/exceptions.py のテスト。"""

import pytest

from app.scrapers.exceptions import (
    FilmarksError,
    FilmarksNotFoundError,
    FilmarksParseError,
    FilmarksUnavailableError,
)


def test_filmarks_error_is_base_of_all():
    """FilmarksError がすべてのサブクラスの基底であること。"""
    assert issubclass(FilmarksUnavailableError, FilmarksError)
    assert issubclass(FilmarksNotFoundError, FilmarksError)
    assert issubclass(FilmarksParseError, FilmarksError)


def test_all_exceptions_inherit_builtin_exception():
    assert issubclass(FilmarksError, Exception)
    assert issubclass(FilmarksUnavailableError, Exception)
    assert issubclass(FilmarksNotFoundError, Exception)
    assert issubclass(FilmarksParseError, Exception)


def test_exceptions_are_distinct_subclasses():
    """3つのサブクラス同士が互いに継承関係を持たないこと。"""
    assert not issubclass(FilmarksUnavailableError, FilmarksNotFoundError)
    assert not issubclass(FilmarksNotFoundError, FilmarksParseError)
    assert not issubclass(FilmarksParseError, FilmarksUnavailableError)


def test_can_raise_and_catch_each_exception():
    for exc_type in (
        FilmarksUnavailableError,
        FilmarksNotFoundError,
        FilmarksParseError,
    ):
        with pytest.raises(exc_type):
            raise exc_type("テスト用メッセージ")


def test_message_preserved():
    with pytest.raises(FilmarksNotFoundError) as exc_info:
        raise FilmarksNotFoundError("ページが見つかりません")
    assert "ページが見つかりません" in str(exc_info.value)


def test_catching_base_catches_nested():
    """基底例外で捕捉できること（共通ハンドラの前提）。"""
    with pytest.raises(FilmarksError):
        raise FilmarksUnavailableError("一時的な障害")