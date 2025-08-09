from __future__ import annotations
import sqlite3
import json
import os
from typing import Optional, List, Tuple

DB_PATH = os.path.join(os.path.expanduser("~"), ".othello_coach.sqlite")

SCHEMA = r"""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS positions (
  hash INTEGER PRIMARY KEY,
  black INTEGER NOT NULL,
  white INTEGER NOT NULL,
  stm   INTEGER NOT NULL,
  ply   INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS analyses (
  hash INTEGER,
  depth INTEGER,
  score INTEGER,
  flag  INTEGER,
  best_move INTEGER,
  nodes INTEGER,
  time_ms INTEGER,
  PRIMARY KEY (hash, depth)
);
CREATE TABLE IF NOT EXISTS moves (
  from_hash INTEGER,
  move INTEGER,
  to_hash INTEGER,
  visit_count INTEGER DEFAULT 0,
  wins INTEGER DEFAULT 0,
  draws INTEGER DEFAULT 0,
  losses INTEGER DEFAULT 0,
  avg_score REAL,
  PRIMARY KEY (from_hash, move)
);
CREATE TABLE IF NOT EXISTS games (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_hash INTEGER,
  result INTEGER,
  length INTEGER,
  tags TEXT,
  pgn TEXT
);
CREATE TABLE IF NOT EXISTS node_attrs (
  hash INTEGER PRIMARY KEY,
  depth INTEGER,
  score_side INTEGER,
  score_white INTEGER,
  score_black INTEGER,
  mob_self INTEGER,
  mob_opp INTEGER,
  first_corner INTEGER,
  stable_discs INTEGER,
  frontier_discs INTEGER,
  parity INTEGER,
  solved TEXT,
  solved_margin INTEGER,
  updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""

_conn: Optional[sqlite3.Connection] = None

def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL;")
        _conn.executescript(SCHEMA)
    return _conn


def upsert_position(hashv:int, black:int, white:int, stm:int, ply:int=0):
    c = get_conn()
    c.execute(
        "INSERT OR REPLACE INTO positions(hash,black,white,stm,ply) VALUES(?,?,?,?,?)",
        (hashv, black, white, stm, ply)
    )
    c.commit()


def upsert_analysis(hashv:int, depth:int, score:int, flag:int, best_move:int, nodes:int, time_ms:int):
    c = get_conn()
    c.execute(
        "INSERT OR REPLACE INTO analyses(hash,depth,score,flag,best_move,nodes,time_ms) VALUES(?,?,?,?,?,?,?)",
        (hashv, depth, score, flag, best_move, nodes, time_ms)
    )
    c.commit()


def record_move(from_hash:int, move:int, to_hash:int, score:Optional[float]=None, outcome:Optional[int]=None):
    c = get_conn()
    # Basic upsert/update of stats
    row = c.execute("SELECT visit_count,wins,draws,losses,avg_score FROM moves WHERE from_hash=? AND move=?", (from_hash, move)).fetchone()
    if row is None:
        wins=draws=losses=0
        if outcome == 1: wins=1
        elif outcome == 0: draws=1
        elif outcome == -1: losses=1
        c.execute("INSERT INTO moves(from_hash,move,to_hash,visit_count,wins,draws,losses,avg_score) VALUES(?,?,?,?,?,?,?,?)",
                  (from_hash, move, to_hash, 1, wins, draws, losses, score if score is not None else None))
    else:
        vc, w, d, l, avg = row
        vc += 1
        if outcome == 1: w += 1
        elif outcome == 0: d += 1
        elif outcome == -1: l += 1
        if score is not None:
            if avg is None:
                avg = score
            else:
                avg = (avg*(vc-1) + score)/vc
        c.execute("UPDATE moves SET visit_count=?,wins=?,draws=?,losses=?,avg_score=?,to_hash=? WHERE from_hash=? AND move=?",
                  (vc, w, d, l, avg, to_hash, from_hash, move))
    c.commit()


def record_game(start_hash:int, result:int, length:int, tags:dict, pgn:str) -> int:
    c = get_conn()
    c.execute("INSERT INTO games(start_hash,result,length,tags,pgn) VALUES(?,?,?, ?, ?)",
              (start_hash, result, length, json.dumps(tags), pgn))
    gid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    c.commit()
    return int(gid)


