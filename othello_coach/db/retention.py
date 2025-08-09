from __future__ import annotations

import sqlite3


def cap_moves_per_position(conn: sqlite3.Connection, cap: int) -> None:
    conn.execute(
        "DELETE FROM moves WHERE rowid IN (SELECT rowid FROM moves ORDER BY visits ASC LIMIT (SELECT CASE WHEN COUNT(*)> ? THEN COUNT(*)-? ELSE 0 END FROM moves))",
        (cap, cap),
    )
