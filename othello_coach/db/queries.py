from __future__ import annotations

import sqlite3
from typing import Optional


def get_position(conn: sqlite3.Connection, h: int) -> Optional[tuple[int, int, int, int, int]]:
    cur = conn.execute("SELECT hash,black,white,stm,ply FROM positions WHERE hash=?", (h,))
    return cur.fetchone()
