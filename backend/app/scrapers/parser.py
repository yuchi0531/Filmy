"""Filmarks のエラーページ検出と共通パースヘルパー。"""

import json
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.scrapers.exceptions import (
    FilmarksNotFoundError,
    FilmarksParseError,
    FilmarksUnavailableError,
)

# エラーページ検出用のテキスト
_UNAVAILABLE_TEXT = "一時的にアクセスできない状態です。"
_NOT_FOUND_TEXT = "お探しのページは見つかりません。"


def to_int(value: Any) -> int | None:
    """``int()`` に変換できる場合は整数を返し、できなければ ``None`` を返す。

    数値文字列でない値（``None`` / 空文字 / 不正な文字列）でも例外を出さない安全な変換。
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> float | None:
    """``float()`` に変換できる場合は小数を返し、できなければ ``None`` を返す。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def check_error_page(soup: BeautifulSoup) -> None:
    """Filmarks のエラーページを検出し、該当すれば例外を投げる。

    - ``p.main__text`` が「一時的にアクセスできない状態です。」で始まる
      → :class:`FilmarksUnavailableError`
    - ``p.main__status-ja`` が「お探しのページは見つかりません。」
      → :class:`FilmarksNotFoundError`
    """
    main_text = soup.select_one("p.main__text")
    if main_text and main_text.get_text(strip=True).startswith(_UNAVAILABLE_TEXT):
        raise FilmarksUnavailableError("Filmarks が一時的にアクセスできない状態です。")

    main_status = soup.select_one("p.main__status-ja")
    if main_status and main_status.get_text(strip=True).startswith(_NOT_FOUND_TEXT):
        raise FilmarksNotFoundError("お探しのページは見つかりません（404相当）。")


def parse_data_attr(element: Tag, attr_name: str) -> dict[str, Any]:
    """``data-mark`` / ``data-clip`` 等のJSON属性をパースして dict で返す。

    例: ``data-mark='{"movie_id": 123, "count": 500}'``
    """
    raw = element.get(attr_name)
    if raw is None:
        raise FilmarksParseError(f"要素に属性 {attr_name} がありません。")
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise FilmarksParseError(
            f"属性 {attr_name} のJSONパースに失敗: {raw[:100]!r}"
        ) from exc
    if not isinstance(data, dict):
        raise FilmarksParseError(
            f"属性 {attr_name} がJSONオブジェクトではありません: {data!r}"
        )
    return data
