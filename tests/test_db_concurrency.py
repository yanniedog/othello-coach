import multiprocessing as mp
import os
import sqlite3
import time

from othello_coach.db.writer import DBWriter


def test_db_writer_spam_events(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    q: mp.Queue = mp.Queue()
    w = DBWriter(str(db_path), q, stall_timeout_s=5.0, checkpoint_interval_s=2.0)
    w.start()
    start = time.perf_counter()
    # flood some events
    for i in range(500):
        q.put({"op": "pos", "payload": {"hash": i, "black": i, "white": i, "stm": 0, "ply": 0}})
        q.put({"op": "note", "payload": {"hash": i, "text": "n"}})
    # allow writer to process
    time.sleep(2.0)
    # sanity: open DB and check counts
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM positions")
        npos = cur.fetchone()[0]
        assert npos >= 900
        cur = conn.execute("SELECT COUNT(*) FROM notes")
        nnotes = cur.fetchone()[0]
        assert nnotes >= 900
    finally:
        conn.close()
    # request graceful shutdown
    q.put({"op": "shutdown", "payload": {}})
    w.join(timeout=2)

