"""app/scrapers/parser.py のテスト。"""

from bs4 import BeautifulSoup
import pytest

from app.scrapers.exceptions import (
    FilmarksNotFoundError,
    FilmarksParseError,
    FilmarksUnavailableError,
)
from app.scrapers.parser import check_error_page, parse_data_attr, to_float, to_int
from tests import mock_html


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        (mock_html.UNAVAILABLE_PAGE_HTML, FilmarksUnavailableError),
        (mock_html.NOT_FOUND_PAGE_HTML, FilmarksNotFoundError),
    ],
)
def test_check_error_page_raises(html, expected):
    soup = BeautifulSoup(html, "lxml")
    with pytest.raises(expected):
        check_error_page(soup)


def test_check_error_page_normal_page_no_exception(make_soup):
    """エラーでないページでは例外が出ない。"""
    soup = make_soup(mock_html.NORMAL_PAGE_HTML)
    # 例外が出なければテスト成功
    check_error_page(soup)


def test_check_error_page_empty_html(make_soup):
    """テキストのみのHTML（エラー要素なし）では例外が出ない。"""
    soup = make_soup("<html><body>ただのテキスト</body></html>")
    check_error_page(soup)


# --- to_int ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("42", 42),
        ("  7  ", 7),
        (123, 123),
        ("1,000", None),  # カンマは int() では変換できない
        ("3.7", None),
        ("abc", None),
        ("", None),
        (None, None),
    ],
)
def test_to_int(value, expected):
    assert to_int(value) == expected


# --- to_float ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3.5", 3.5),
        ("4", 4.0),
        ("  1.25  ", 1.25),
        (2, 2.0),
        ("abc", None),
        ("", None),
        (None, None),
    ],
)
def test_to_float(value, expected):
    assert to_float(value) == expected


# --- parse_data_attr ---


def test_parse_data_attr_valid_json():
    el = BeautifulSoup(
        '<div data-mark=\'{"movie_id": 123, "count": 456}\'></div>', "lxml"
    ).find("div")
    data = parse_data_attr(el, "data-mark")
    assert data == {"movie_id": 123, "count": 456}


def test_parse_data_attr_invalid_json_raises():
    el = BeautifulSoup('<div data-mark="not-json"></div>', "lxml").find("div")
    with pytest.raises(FilmarksParseError):
        parse_data_attr(el, "data-mark")


def test_parse_data_attr_missing_attr_raises():
    el = BeautifulSoup("<div></div>", "lxml").find("div")
    with pytest.raises(FilmarksParseError):
        parse_data_attr(el, "data-mark")


def test_parse_data_attr_non_object_json_raises():
    el = BeautifulSoup('<div data-mark="[1, 2, 3]"></div>', "lxml").find("div")
    with pytest.raises(FilmarksParseError):
        parse_data_attr(el, "data-mark")