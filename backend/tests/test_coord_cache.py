"""app/coord_cache.py のテスト（SQLite 永続キャッシュ）。"""

import os
import sqlite3

from app.coord_cache import CoordCache


def test_set_and_get(tmp_path):
    cache = CoordCache(str(tmp_path / "theater_coords.db"))
    assert cache.get("172") is None

    cache.set("172", 35.6905, 139.7036, address="東京都新宿区新宿3-1-1")

    assert cache.get("172") == (35.6905, 139.7036)


def test_get_missing_returns_none(tmp_path):
    cache = CoordCache(str(tmp_path / "theater_coords.db"))
    assert cache.get("9999") is None


def test_set_overwrites_existing(tmp_path):
    cache = CoordCache(str(tmp_path / "theater_coords.db"))
    cache.set("172", 35.0, 139.0)
    cache.set("172", 36.0, 140.0)

    assert cache.get("172") == (36.0, 140.0)


def test_persists_across_instances(tmp_path):
    """別インスタンス（再起動相当）でも座標を再読み込みできること。"""
    db_path = str(tmp_path / "theater_coords.db")

    first = CoordCache(db_path)
    first.set("172", 35.6905, 139.7036, address="東京都新宿区新宿3-1-1")

    second = CoordCache(db_path)
    assert second.get("172") == (35.6905, 139.7036)


def test_creates_parent_directory(tmp_path):
    """親ディレクトリが無くても自動生成されること。"""
    db_path = str(tmp_path / "nested" / "dir" / "theater_coords.db")
    cache = CoordCache(db_path)
    cache.set("172", 35.0, 139.0)

    assert os.path.exists(db_path)


def test_table_schema(tmp_path):
    """テーブルが期待するスキーマで作成されること。"""
    db_path = str(tmp_path / "theater_coords.db")
    cache = CoordCache(db_path)
    cache.set("172", 35.6905, 139.7036, address="東京都新宿区新宿3-1-1")

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT theater_id, latitude, longitude, address, updated_at "
            "FROM theater_coords WHERE theater_id = '172'"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row[0] == "172"
    assert row[1] == 35.6905
    assert row[2] == 139.7036
    assert row[3] == "東京都新宿区新宿3-1-1"
    assert row[4]  # updated_at が保存されている
