from __future__ import annotations

import multiprocessing as mp
import queue
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os
import pathlib
import orjson

from .schema_sql_loader import get_schema_sql
from .retention import cap_moves_per_position


@dataclass
class WriterConfig:
    path: str
    busy_timeout_ms: int = 4000


class DBWriter(mp.Process):
    def __init__(
        self,
        db_path: str,
        in_queue: mp.Queue,
        stall_timeout_s: float = 30.0,
        checkpoint_interval_s: float = 600.0,
        busy_timeout_ms: int = 4000,
        wal_checkpoint_mb: int = 100,
        log_path: Optional[str] = None,
    ):
        super().__init__(daemon=True)
        self.db_path = db_path
        self.in_queue = in_queue
        self.batch: List[Dict[str, Any]] = []
        self.last_checkpoint = time.monotonic()
        self.last_progress = time.monotonic()
        self.stall_timeout_s = stall_timeout_s
        self.checkpoint_interval_s = checkpoint_interval_s
        self.stats = {"received": 0, "applied": 0, "flushes": 0, "last_batch": 0}
        self.busy_timeout_ms = busy_timeout_ms
        self.wal_checkpoint_mb = wal_checkpoint_mb
        if log_path is None:
            default_lp = os.path.expanduser("~/.othello_coach/writer.log")
            self.log_path = pathlib.Path(default_lp)
        else:
            self.log_path = pathlib.Path(log_path)

    def _log(self, event: str, **kwargs: Any) -> None:
        payload = {
            "ts": time.time(),
            "module": "db.writer",
            "event": event,
            "stats": self.stats,
        }
        payload.update(kwargs)
        try:
            line = orjson.dumps(payload).decode("utf-8")
            print(line, flush=True)
            if self.log_path is not None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception:
            pass

    def _should_checkpoint_by_size(self) -> bool:
        wal_path = self.db_path + "-wal"
        try:
            size = os.path.getsize(wal_path)
        except OSError:
            return False
        return size > self.wal_checkpoint_mb * 1024 * 1024

    def run(self) -> None:
        conn = sqlite3.connect(self.db_path)
        # Apply PRAGMAs per spec on connection open
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA cache_size=-131072;")
        conn.execute("PRAGMA mmap_size=268435456;")
        conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        conn.executescript(get_schema_sql())
        last_flush = time.monotonic()
        self._log("start", db_path=self.db_path)
        alive = True
        while alive:
            try:
                msg = self.in_queue.get(timeout=0.25)
                # Allow graceful shutdown
                if msg.get("op") == "shutdown":
                    alive = False
                else:
                    self.batch.append(msg)
                    self.stats["received"] += 1
            except queue.Empty:
                pass
            now = time.monotonic()
            if self.batch and (now - last_flush > 0.25 or len(self.batch) >= 500):
                t0 = time.perf_counter()
                with conn:
                    for m in self.batch:
                        self._apply(conn, m)
                t_ms = int((time.perf_counter() - t0) * 1000)
                n = len(self.batch)
                self.batch.clear()
                last_flush = now
                self.last_progress = now
                self.stats["flushes"] += 1
                self.stats["last_batch"] = n
                self.stats["last_flush_ms"] = t_ms
                # EWMA for avg flush
                prev = self.stats.get("avg_flush_ms", t_ms)
                self.stats["avg_flush_ms"] = int(0.8 * prev + 0.2 * t_ms)
                self._log("flush", batch=n, flush_ms=t_ms)
            # Periodic WAL checkpoint every 10 minutes or if WAL size exceeds threshold
            if (now - self.last_checkpoint > self.checkpoint_interval_s) or self._should_checkpoint_by_size():
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except sqlite3.DatabaseError:
                    pass
                self.last_checkpoint = now
                self._log("checkpoint")
            # Stall watchdog: if no progress for too long, exit
            if now - self.last_progress > self.stall_timeout_s:
                try:
                    conn.close()
                finally:
                    os._exit(1)
        try:
            conn.close()
        finally:
            self._log("shutdown")

    def _apply(self, conn: sqlite3.Connection, msg: Dict[str, Any]) -> None:
        op = msg.get("op")
        p = msg.get("payload", {})
        if op == "pos":
            conn.execute(
                "INSERT OR REPLACE INTO positions(hash,black,white,stm,ply) VALUES(?,?,?,?,?)",
                (p["hash"], p["black"], p["white"], p["stm"], p["ply"]),
            )
            self.stats["applied"] += 1
        elif op == "ana":
            conn.execute(
                "INSERT OR REPLACE INTO analyses(hash,depth,score,flag,best_move,nodes,time_ms,engine_ver) VALUES(?,?,?,?,?,?,?,?)",
                (p["hash"], p["depth"], p["score"], p["flag"], p.get("best_move"), p["nodes"], p["time_ms"], p["engine_ver"]),
            )
            self.stats["applied"] += 1
        elif op == "move":
            conn.execute(
                "INSERT OR REPLACE INTO moves(from_hash,move,to_hash,visits,wins,draws,losses,avg_score,novelty) VALUES(?,?,?,?,?,?,?,?,?)",
                (p["from_hash"], p["move"], p["to_hash"], p["visits"], p["wins"], p["draws"], p["losses"], p["avg_score"], p["novelty"]),
            )
            self.stats["applied"] += 1
        elif op == "feat":
            conn.execute(
                "INSERT OR REPLACE INTO features(hash,mobility,pot_mob,frontier,stability,parity,corners,x_squares,computed_engine_ver) VALUES(?,?,?,?,?,?,?,?,?)",
                (p["hash"], p.get("mobility"), p.get("pot_mob"), p.get("frontier"), p.get("stability"), p.get("parity"), p.get("corners"), p.get("x_squares"), p["computed_engine_ver"]),
            )
            self.stats["applied"] += 1
        elif op == "game":
            conn.execute(
                "INSERT INTO games(start_hash,result,length,tags,moves,started_at,finished_at) VALUES(?,?,?,?,?,?,?)",
                (p["start_hash"], p["result"], p["length"], p.get("tags"), p["moves"], p.get("started_at"), p.get("finished_at")),
            )
            self.stats["applied"] += 1
        elif op == "note":
            conn.execute(
                "INSERT OR REPLACE INTO notes(hash,text) VALUES(?,?)",
                (p["hash"], p["text"]),
            )
            self.stats["applied"] += 1
        # Other ops can be added similarly
