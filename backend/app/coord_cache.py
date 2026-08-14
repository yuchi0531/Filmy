"""劇場ID → 座標（緯度・経度）の SQLite 永続キャッシュ。

劇場は移動しないため、一度ジオコーディングで得た座標は不変とみなして
SQLite に永続化する。Koyeb 等でプロセスが再起動しても座標を再取得する
必要がなくなる（国土地理院APIへの負荷とFilmarksへの追加アクセスを削減）。

ファイル・テーブルの生成は初回アクセス時に遅延実行するため、インスタンス
生成（モジュール import）自体には副作用が無い。
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS theater_coords (
    theater_id TEXT PRIMARY KEY,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    address TEXT,
    updated_at TEXT
)
"""


class CoordCache:
    """SQLite で劇場座標を永続化するスレッドセーフなキャッシュ。

    - ``get(theater_id)``: 座標 ``(緯度, 経度)`` を返す（無ければ ``None``）
    - ``set(theater_id, latitude, longitude, address)``: 座標を保存する
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """DBファイルとテーブルを初回アクセス時に生成する。"""
        if self._initialized:
            return
        parent = os.path.dirname(self._db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()
        self._initialized = True

    def _connect(self) -> sqlite3.Connection:
        # check_same_thread=False により、ロックで直列化された
        # 複数スレッドからの接続を許容する。
        return sqlite3.connect(self._db_path, check_same_thread=False)

    def get(self, theater_id: str) -> tuple[float, float] | None:
        with self._lock:
            self._ensure_initialized()
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT latitude, longitude FROM theater_coords WHERE theater_id = ?",
                    (theater_id,),
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        return float(row[0]), float(row[1])

    def set(
        self,
        theater_id: str,
        latitude: float,
        longitude: float,
        address: str | None = None,
    ) -> None:
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._ensure_initialized()
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT INTO theater_coords
                        (theater_id, latitude, longitude, address, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(theater_id) DO UPDATE SET
                        latitude = excluded.latitude,
                        longitude = excluded.longitude,
                        address = excluded.address,
                        updated_at = excluded.updated_at
                    """,
                    (theater_id, float(latitude), float(longitude), address, updated_at),
                )
                conn.commit()
            finally:
                conn.close()
