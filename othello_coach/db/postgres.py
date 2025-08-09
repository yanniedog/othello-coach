"""PostgreSQL adapter for Othello Coach"""

from typing import Dict, Any, Optional
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, DateTime, Real, Index
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PostgresAdapter:
    """PostgreSQL database adapter"""
    
    def __init__(self, dsn: str, analyses_partition_by_depth: bool = True):
        self.dsn = dsn
        self.partition_by_depth = analyses_partition_by_depth
        self.engine = None
        self.Session = None
        self._setup_connection()
    
    def _setup_connection(self):
        """Setup PostgreSQL connection"""
        try:
            self.engine = create_engine(
                self.dsn,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            self.Session = sessionmaker(bind=self.engine)
            logger.info("PostgreSQL connection established")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def create_schema(self):
        """Create PostgreSQL schema with partitioning"""
        with self.Session() as session:
            # Create main tables
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS positions(
                    hash BIGINT PRIMARY KEY,
                    black BIGINT NOT NULL,
                    white BIGINT NOT NULL,
                    stm INTEGER NOT NULL,
                    ply INTEGER NOT NULL
                )
            """))
            
            if self.partition_by_depth:
                # Create partitioned analyses table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS analyses(
                        hash BIGINT NOT NULL,
                        depth INTEGER NOT NULL,
                        score INTEGER NOT NULL,
                        flag INTEGER NOT NULL,
                        best_move INTEGER,
                        nodes BIGINT NOT NULL,
                        time_ms INTEGER NOT NULL,
                        engine_ver TEXT NOT NULL,
                        win_prob REAL DEFAULT NULL,
                        PRIMARY KEY(hash, depth)
                    ) PARTITION BY RANGE (depth)
                """))
                
                # Create partitions for common depth ranges
                depth_ranges = [
                    (1, 4), (4, 8), (8, 12), (12, 16), (16, 20), (20, 999)
                ]
                
                for min_depth, max_depth in depth_ranges:
                    partition_name = f"analyses_d{min_depth}_{max_depth}"
                    session.execute(text(f"""
                        CREATE TABLE IF NOT EXISTS {partition_name}
                        PARTITION OF analyses
                        FOR VALUES FROM ({min_depth}) TO ({max_depth})
                    """))
                    
                    # Create index on each partition
                    session.execute(text(f"""
                        CREATE INDEX IF NOT EXISTS idx_{partition_name}_depth
                        ON {partition_name} (depth)
                        WHERE depth >= 8
                    """))
            else:
                # Standard non-partitioned table
                session.execute(text("""
                    CREATE TABLE IF NOT EXISTS analyses(
                        hash BIGINT NOT NULL,
                        depth INTEGER NOT NULL,
                        score INTEGER NOT NULL,
                        flag INTEGER NOT NULL,
                        best_move INTEGER,
                        nodes BIGINT NOT NULL,
                        time_ms INTEGER NOT NULL,
                        engine_ver TEXT NOT NULL,
                        win_prob REAL DEFAULT NULL,
                        PRIMARY KEY(hash, depth)
                    )
                """))
                
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_analyses_dge8 
                    ON analyses(depth) WHERE depth >= 8
                """))
            
            # Other tables
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS moves(
                    from_hash BIGINT NOT NULL,
                    move INTEGER NOT NULL,
                    to_hash BIGINT NOT NULL,
                    visits INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    draws INTEGER NOT NULL,
                    losses INTEGER NOT NULL,
                    avg_score REAL NOT NULL,
                    novelty REAL NOT NULL,
                    PRIMARY KEY(from_hash, move)
                )
            """))
            
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_moves_to ON moves(to_hash)
            """))
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS features(
                    hash BIGINT PRIMARY KEY,
                    mobility INTEGER,
                    pot_mob INTEGER,
                    frontier INTEGER,
                    stability INTEGER,
                    parity INTEGER,
                    corners INTEGER,
                    x_squares INTEGER,
                    computed_engine_ver TEXT NOT NULL,
                    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS games(
                    id SERIAL PRIMARY KEY,
                    start_hash BIGINT NOT NULL,
                    result INTEGER NOT NULL,
                    length INTEGER NOT NULL,
                    tags TEXT,
                    moves TEXT NOT NULL,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP
                )
            """))
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS notes(
                    hash BIGINT PRIMARY KEY,
                    text TEXT
                )
            """))
            
            # PostgreSQL full-text search
            session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_notes_fts 
                ON notes USING gin(to_tsvector('english', text))
            """))
            
            # V1.1 tables
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS trainer(
                    hash BIGINT PRIMARY KEY,
                    box INTEGER NOT NULL DEFAULT 1,
                    due DATE,
                    streak INTEGER NOT NULL DEFAULT 0,
                    suspended INTEGER NOT NULL DEFAULT 0
                )
            """))
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS ladders(
                    engine_ver TEXT NOT NULL,
                    profile TEXT NOT NULL,
                    rating REAL NOT NULL,
                    rd REAL NOT NULL,
                    last_rated_at TIMESTAMP NOT NULL,
                    PRIMARY KEY(engine_ver, profile)
                )
            """))
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS mappings(
                    engine_ver TEXT PRIMARY KEY,
                    json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """))
            
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS gdl_programs(
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    ast_json TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """))
            
            session.commit()
            logger.info("PostgreSQL schema created successfully")
    
    def migrate_from_sqlite(self, sqlite_path: str):
        """Migrate data from SQLite to PostgreSQL"""
        import sqlite3
        
        logger.info(f"Starting migration from SQLite: {sqlite_path}")
        
        # Connect to SQLite
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.row_factory = sqlite3.Row
        
        try:
            with self.Session() as pg_session:
                # Migrate positions
                sqlite_cursor = sqlite_conn.execute("SELECT * FROM positions")
                positions = sqlite_cursor.fetchall()
                
                if positions:
                    logger.info(f"Migrating {len(positions)} positions...")
                    for pos in positions:
                        pg_session.execute(text("""
                            INSERT INTO positions (hash, black, white, stm, ply)
                            VALUES (:hash, :black, :white, :stm, :ply)
                            ON CONFLICT (hash) DO NOTHING
                        """), dict(pos))
                
                # Migrate analyses
                sqlite_cursor = sqlite_conn.execute("SELECT * FROM analyses")
                analyses = sqlite_cursor.fetchall()
                
                if analyses:
                    logger.info(f"Migrating {len(analyses)} analyses...")
                    for analysis in analyses:
                        pg_session.execute(text("""
                            INSERT INTO analyses (hash, depth, score, flag, best_move, nodes, time_ms, engine_ver, win_prob)
                            VALUES (:hash, :depth, :score, :flag, :best_move, :nodes, :time_ms, :engine_ver, :win_prob)
                            ON CONFLICT (hash, depth) DO NOTHING
                        """), dict(analysis))
                
                # Migrate other tables similarly...
                for table_name in ['moves', 'features', 'games', 'notes']:
                    try:
                        sqlite_cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
                        rows = sqlite_cursor.fetchall()
                        
                        if rows:
                            logger.info(f"Migrating {len(rows)} {table_name} records...")
                            for row in rows:
                                # Build INSERT statement dynamically
                                columns = list(row.keys())
                                placeholders = [f":{col}" for col in columns]
                                
                                if table_name == 'games':
                                    conflict_clause = "ON CONFLICT (id) DO NOTHING"
                                elif table_name in ['notes', 'features']:
                                    conflict_clause = "ON CONFLICT (hash) DO NOTHING"
                                else:
                                    conflict_clause = "ON CONFLICT DO NOTHING"
                                
                                query = f"""
                                    INSERT INTO {table_name} ({', '.join(columns)})
                                    VALUES ({', '.join(placeholders)})
                                    {conflict_clause}
                                """
                                pg_session.execute(text(query), dict(row))
                    
                    except Exception as e:
                        logger.warning(f"Failed to migrate {table_name}: {e}")
                
                pg_session.commit()
                logger.info("Migration completed successfully")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
        finally:
            sqlite_conn.close()
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information and statistics"""
        with self.Session() as session:
            # Get PostgreSQL version
            version_result = session.execute(text("SELECT version()")).fetchone()
            
            # Get table sizes
            table_sizes = {}
            tables = ['positions', 'analyses', 'moves', 'features', 'games', 'notes', 
                     'trainer', 'ladders', 'mappings', 'gdl_programs']
            
            for table in tables:
                try:
                    size_result = session.execute(text(f"""
                        SELECT 
                            schemaname, 
                            tablename, 
                            attname, 
                            n_distinct, 
                            correlation
                        FROM pg_stats 
                        WHERE tablename = :table_name
                        LIMIT 1
                    """), {'table_name': table}).fetchone()
                    
                    count_result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
                    table_sizes[table] = count_result[0] if count_result else 0
                    
                except Exception:
                    table_sizes[table] = 0
            
            return {
                'database_type': 'PostgreSQL',
                'version': version_result[0] if version_result else 'Unknown',
                'partitioned': self.partition_by_depth,
                'table_sizes': table_sizes
            }
    
    def optimize_database(self):
        """Run PostgreSQL optimization"""
        with self.Session() as session:
            logger.info("Running PostgreSQL optimization...")
            
            # Update table statistics
            session.execute(text("ANALYZE"))
            
            # Vacuum analyze for better performance
            session.execute(text("VACUUM ANALYZE"))
            
            logger.info("PostgreSQL optimization completed")
    
    def search_notes_fts(self, query: str, limit: int = 10) -> list:
        """Full-text search in notes using PostgreSQL"""
        with self.Session() as session:
            result = session.execute(text("""
                SELECT 
                    hash,
                    text,
                    ts_rank(to_tsvector('english', text), plainto_tsquery('english', :query)) as rank
                FROM notes
                WHERE to_tsvector('english', text) @@ plainto_tsquery('english', :query)
                ORDER BY rank DESC
                LIMIT :limit
            """), {'query': query, 'limit': limit}).fetchall()
            
            return [
                {
                    'hash': row.hash,
                    'text': row.text,
                    'relevance': float(row.rank)
                }
                for row in result
            ]
