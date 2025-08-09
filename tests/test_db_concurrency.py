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
    # allow writer to process and retry for up to 3 seconds
    time.sleep(0.2)
    deadline = time.time() + 5.0
    npos = nnotes = 0
    while time.time() < deadline:
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                cur = conn.execute("SELECT COUNT(*) FROM positions")
                npos = cur.fetchone()[0]
                cur = conn.execute("SELECT COUNT(*) FROM notes")
                nnotes = cur.fetchone()[0]
            finally:
                conn.close()
        except sqlite3.OperationalError:
            # tables not created yet; wait and retry
            time.sleep(0.1)
            continue
        if npos >= 480 and nnotes >= 480:
            break
        time.sleep(0.1)
    assert npos >= 480
    assert nnotes >= 480
    # request graceful shutdown
    q.put({"op": "shutdown", "payload": {}})
    w.join(timeout=2)

