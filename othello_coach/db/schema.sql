CREATE TABLE IF NOT EXISTS positions(
  hash INTEGER PRIMARY KEY,
  black INTEGER NOT NULL,
  white INTEGER NOT NULL,
  stm   INTEGER NOT NULL,
  ply   INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS analyses(
  hash INTEGER NOT NULL,
  depth INTEGER NOT NULL,
  score INTEGER NOT NULL,
  flag  INTEGER NOT NULL,
  best_move INTEGER,
  nodes INTEGER NOT NULL,
  time_ms INTEGER NOT NULL,
  engine_ver TEXT NOT NULL,
  PRIMARY KEY(hash, depth)
);
CREATE INDEX IF NOT EXISTS idx_analyses_dge8 ON analyses(depth) WHERE depth >= 8;
CREATE TABLE IF NOT EXISTS moves(
  from_hash INTEGER NOT NULL,
  move INTEGER NOT NULL,
  to_hash INTEGER NOT NULL,
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
  hash INTEGER PRIMARY KEY,
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
  start_hash INTEGER NOT NULL,
  result INTEGER NOT NULL,
  length INTEGER NOT NULL,
  tags TEXT,
  moves TEXT NOT NULL,
  started_at DATETIME,
  finished_at DATETIME
);
CREATE TABLE IF NOT EXISTS notes(
  hash INTEGER PRIMARY KEY,
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
