from __future__ import annotations

import sqlite3
from .schema_sql_loader import get_schema_sql


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(get_schema_sql())
