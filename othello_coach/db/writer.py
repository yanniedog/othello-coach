from __future__ import annotations

import multiprocessing as mp
import queue
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List
import os

from .schema_sql_loader import get_schema_sql
from .retention import cap_moves_per_position


@dataclass
class WriterConfig:
    path: str
    busy_timeout_ms: int = 4000


class DBWriter(mp.Process):
    def __init__(self, db_path: str, in_queue: mp.Queue, stall_timeout_s: float = 30.0, checkpoint_interval_s: float = 600.0):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.in_queue = in_queue
        self.batch: List[Dict[str, Any]] = []
        self.last_checkpoint = time.monotonic()
        self.last_progress = time.monotonic()
        self.stall_timeout_s = stall_timeout_s
        self.checkpoint_interval_s = checkpoint_interval_s

    def run(self) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(f"PRAGMA busy_timeout={4000}")
        conn.executescript(get_schema_sql())
        last_flush = time.monotonic()
        alive = True
        while alive:
            try:
                msg = self.in_queue.get(timeout=0.25)
                # Allow graceful shutdown
                if msg.get("op") == "shutdown":
                    alive = False
                else:
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
                self.last_progress = now
            # Periodic WAL checkpoint every 10 minutes
            if now - self.last_checkpoint > self.checkpoint_interval_s:
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except sqlite3.DatabaseError:
                    pass
                self.last_checkpoint = now
            # Stall watchdog: if no progress for too long, exit
            if now - self.last_progress > self.stall_timeout_s:
                try:
                    conn.close()
                finally:
                    os._exit(1)

    def _apply(self, conn: sqlite3.Connection, msg: Dict[str, Any]) -> None:
        op = msg.get("op")
        p = msg.get("payload", {})
        if op == "pos":
            conn.execute(
                "INSERT OR REPLACE INTO positions(hash,black,white,stm,ply) VALUES(?,?,?,?,?)",
                (p["hash"], p["black"], p["white"], p["stm"], p["ply"]),
            )
        elif op == "ana":
            conn.execute(
                "INSERT OR REPLACE INTO analyses(hash,depth,score,flag,best_move,nodes,time_ms,engine_ver) VALUES(?,?,?,?,?,?,?,?)",
                (p["hash"], p["depth"], p["score"], p["flag"], p.get("best_move"), p["nodes"], p["time_ms"], p["engine_ver"]),
            )
        elif op == "move":
            conn.execute(
                "INSERT OR REPLACE INTO moves(from_hash,move,to_hash,visits,wins,draws,losses,avg_score,novelty) VALUES(?,?,?,?,?,?,?,?,?)",
                (p["from_hash"], p["move"], p["to_hash"], p["visits"], p["wins"], p["draws"], p["losses"], p["avg_score"], p["novelty"]),
            )
        elif op == "feat":
            conn.execute(
                "INSERT OR REPLACE INTO features(hash,mobility,pot_mob,frontier,stability,parity,corners,x_squares,computed_engine_ver) VALUES(?,?,?,?,?,?,?,?,?)",
                (p["hash"], p.get("mobility"), p.get("pot_mob"), p.get("frontier"), p.get("stability"), p.get("parity"), p.get("corners"), p.get("x_squares"), p["computed_engine_ver"]),
            )
        elif op == "game":
            conn.execute(
                "INSERT INTO games(start_hash,result,length,tags,moves,started_at,finished_at) VALUES(?,?,?,?,?,?,?)",
                (p["start_hash"], p["result"], p["length"], p.get("tags"), p["moves"], p.get("started_at"), p.get("finished_at")),
            )
        elif op == "note":
            conn.execute(
                "INSERT OR REPLACE INTO notes(hash,text) VALUES(?,?)",
                (p["hash"], p["text"]),
            )
        # Other ops can be added similarly
