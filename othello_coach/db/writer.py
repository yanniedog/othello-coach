from __future__ import annotations

import multiprocessing as mp
import queue
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List

from .schema_sql_loader import get_schema_sql


@dataclass
class WriterConfig:
    path: str
    busy_timeout_ms: int = 4000


class DBWriter(mp.Process):
    def __init__(self, db_path: str, in_queue: mp.Queue):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.in_queue = in_queue
        self.batch: List[Dict[str, Any]] = []

    def run(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(f"PRAGMA busy_timeout={4000}")
        conn.executescript(get_schema_sql())
        last_flush = time.monotonic()
        while True:
            try:
                msg = self.in_queue.get(timeout=0.25)
                self.batch.append(msg)
            except queue.Empty:
                pass
            now = time.monotonic()
            if self.batch and (now - last_flush > 0.25 or len(self.batch) >= 500):
                with conn:
                    for m in self.batch:
                        self._apply(conn, m)
                self.batch.clear()
                last_flush = now

    def _apply(self, conn: sqlite3.Connection, msg: Dict[str, Any]) -> None:
        op = msg.get("op")
        p = msg.get("payload", {})
        if op == "pos":
            conn.execute(
                "INSERT OR REPLACE INTO positions(hash,black,white,stm,ply) VALUES(?,?,?,?,?)",
                (p["hash"], p["black"], p["white"], p["stm"], p["ply"]),
            )
        elif op == "note":
            conn.execute(
                "INSERT OR REPLACE INTO notes(hash,text) VALUES(?,?)",
                (p["hash"], p["text"]),
            )
        # Other ops can be added similarly
