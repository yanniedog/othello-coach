CREATE TABLE IF NOT EXISTS positions(
  hash TEXT PRIMARY KEY,
  black TEXT NOT NULL,
  white TEXT NOT NULL,
  stm   INTEGER NOT NULL,
  ply   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses(
  hash TEXT NOT NULL,
  depth INTEGER NOT NULL,
  score INTEGER NOT NULL,
  flag  INTEGER NOT NULL,
  best_move INTEGER,
  nodes INTEGER NOT NULL,
  time_ms INTEGER NOT NULL,
  engine_ver TEXT NOT NULL,
  win_prob REAL DEFAULT NULL,
  PRIMARY KEY(hash, depth)
);
CREATE INDEX IF NOT EXISTS idx_analyses_dge8 ON analyses(depth) WHERE depth >= 8;
CREATE TABLE IF NOT EXISTS moves(
  from_hash TEXT NOT NULL,
  move INTEGER NOT NULL,
  to_hash TEXT NOT NULL,
  visits INTEGER NOT NULL,
  wins INTEGER NOT NULL,
  draws INTEGER NOT NULL,
  losses INTEGER NOT NULL,
  avg_score REAL NOT NULL,
  novelty REAL NOT NULL,
  PRIMARY KEY(from_hash, move)
);
CREATE INDEX IF NOT EXISTS idx_moves_to ON moves(to_hash);
CREATE TABLE IF NOT EXISTS features(
  hash TEXT PRIMARY KEY,
  mobility INTEGER,
  pot_mob INTEGER,
  frontier INTEGER,
  stability INTEGER,
  parity INTEGER,
  corners INTEGER,
  x_squares INTEGER,
  computed_engine_ver TEXT NOT NULL,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS games(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  start_hash TEXT NOT NULL,
  result INTEGER NOT NULL,
  length INTEGER NOT NULL,
  tags TEXT,
  moves TEXT NOT NULL,
  started_at DATETIME,
  finished_at DATETIME
);
CREATE TABLE IF NOT EXISTS notes(
  hash TEXT PRIMARY KEY,
  text TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(text);
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, text) VALUES (new.hash, new.text);
END;
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, text) VALUES('delete', old.hash, old.text);
  INSERT INTO notes_fts(rowid, text) VALUES (new.hash, new.text);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, text) VALUES('delete', old.hash, old.text);
END;

-- V1.1 Tables
CREATE TABLE IF NOT EXISTS trainer(
  hash TEXT PRIMARY KEY,
  box INTEGER NOT NULL DEFAULT 1,
  due DATE,
  streak INTEGER NOT NULL DEFAULT 0,
  suspended INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ladders(
  engine_ver TEXT NOT NULL,
  profile TEXT NOT NULL,
  rating REAL NOT NULL,
  RD REAL NOT NULL,
  last_rated_at DATETIME NOT NULL,
  PRIMARY KEY(engine_ver, profile)
);

CREATE TABLE IF NOT EXISTS mappings(
  engine_ver TEXT PRIMARY KEY,
  json TEXT NOT NULL,
  created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS gdl_programs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  source TEXT NOT NULL,
  ast_json TEXT NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
