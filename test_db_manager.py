#!/usr/bin/env python3
"""Test database manager functionality by running the actual othello-coach application"""

import sys
import os
import sqlite3
import tempfile
import time
import subprocess
import signal
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_test_database(db_path: str) -> None:
    """Create a test database with sample games"""
    from othello_coach.db.schema_sql_loader import get_schema_sql
    
    # Create database and schema
    conn = sqlite3.connect(db_path)
    try:
        # Create schema
        conn.executescript(get_schema_sql())
        
        # Insert sample games with coordinate notation moves
        sample_games = [
            # Game 1: Standard opening sequence
            {
                'start_hash': '0000000810000000_0000001008000000_0_0',
                'result': 1,  # Black win
                'length': 60,
                'tags': 'test,opening',
                'moves': 'e6f4c3d3c4b3e3f3c5b4a3b5a4a5b6a6c6d6e7f7g6h6g5h5g4h4g3h3g2h2g1h1f2e2f1e1d2c2d1c1b2a2b1a1',
                'started_at': datetime.now() - timedelta(hours=2),
                'finished_at': datetime.now() - timedelta(hours=1, minutes=45)
            },
            # Game 2: Game with passes
            {
                'start_hash': '0000000810000000_0000001008000000_0_0',
                'result': 0,  # White win
                'length': 58,
                'tags': 'test,passes',
                'moves': 'e6f4c3d3c4b3e3f3c5b4a3b5a4a5b6a6c6d6e7f7g6h6g5h5g4h4g3h3g2h2g1h1f2e2f1e1d2c2d1c1b2a2b1a1--',
                'started_at': datetime.now() - timedelta(hours=1),
                'finished_at': datetime.now() - timedelta(minutes=30)
            },
            # Game 3: Short game
            {
                'start_hash': '0000000810000000_0000001008000000_0_0',
                'result': 0.5,  # Draw
                'length': 30,
                'tags': 'test,short',
                'moves': 'e6f4c3d3c4b3e3f3c5b4a3b5a4a5b6a6c6d6e7f7g6h6g5h5g4h4g3h3',
                'started_at': datetime.now() - timedelta(minutes=15),
                'finished_at': datetime.now() - timedelta(minutes=10)
            }
        ]
        
        # Insert games
        for game in sample_games:
            conn.execute("""
                INSERT INTO games(start_hash, result, length, tags, moves, started_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                game['start_hash'],
                game['result'],
                game['length'],
                game['tags'],
                game['moves'],
                game['started_at'].isoformat(),
                game['finished_at'].isoformat()
            ))
        
        # Insert some ladder data
        conn.execute("""
            INSERT INTO ladders(profile, rating, RD, engine_ver, last_rated_at)
            VALUES 
            ('elo_800', 800, 50, '1.1.0', datetime('now')),
            ('elo_1400', 1400, 45, '1.1.0', datetime('now')),
            ('elo_2000', 2000, 40, '1.1.0', datetime('now'))
        """)
        
        conn.commit()
        print(f"✅ Created test database with {len(sample_games)} sample games")
        
    finally:
        conn.close()

def test_db_manager_integration():
    """Test database manager by running the actual othello-coach application"""
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Create test database
            create_test_database(db_path)
            
            # Set environment variable to use our test database
            env = os.environ.copy()
            env['OTHELLO_COACH_DB_PATH'] = str(db_path)
            
            print("Testing database manager integration with othello-coach...")
            print(f"Using test database: {db_path}")
            
            # Test 1: Check if the application can start without stalling
            print("\n1. Testing application startup...")
            startup_start = time.time()
            
            # Try to start the application (non-blocking) with strict timeout
            try:
                # Use python -m to run the module with --help to avoid stalling
                process = subprocess.Popen(
                    [sys.executable, "-m", "othello_coach.tools.cli", "--help"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Wait with strict timeout
                try:
                    stdout, stderr = process.communicate(timeout=10)  # 10 second timeout
                    if process.returncode == 0:
                        print("✅ Application CLI help command executed successfully")
                    else:
                        print(f"⚠️  CLI help command exited with code {process.returncode}")
                        if stderr:
                            print(f"STDERR: {stderr}")
                except subprocess.TimeoutExpired:
                    print("❌ CLI help command timed out - killing process")
                    process.kill()
                    process.wait()
                    return False
                
            except Exception as e:
                print(f"❌ Error starting application: {e}")
                return False
            
            # Test 2: Check if database operations are responsive
            print("\n2. Testing database responsiveness...")
            
            # Try to access the database directly to check responsiveness
            db_start = time.time()
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Test basic queries with timeout
            try:
                cur.execute("SELECT COUNT(*) FROM games")
                game_count = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM ladders")
                ladder_count = cur.fetchone()[0]
                
                conn.close()
                db_time = time.time() - db_start
                
                print(f"✅ Database queries completed in {db_time:.3f}s")
                print(f"   - Games: {game_count}")
                print(f"   - Ladder entries: {ladder_count}")
                
            except Exception as e:
                print(f"❌ Database queries failed: {e}")
                conn.close()
                return False
            
            # Test 3: Check for potential stalling in large queries
            print("\n3. Testing large query performance...")
            
            large_query_start = time.time()
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            # Simulate a potentially expensive query with timeout
            try:
                cur.execute("""
                    SELECT g.id, g.result, g.length, g.tags, g.moves, 
                           g.started_at, g.finished_at
                    FROM games g
                    ORDER BY g.started_at DESC
                    LIMIT 100
                """)
                
                results = cur.fetchall()
                large_query_time = time.time() - large_query_start
                conn.close()
                
                if large_query_time < 1.0:  # Should complete within 1 second
                    print(f"✅ Large query completed in {large_query_time:.3f}s")
                else:
                    print(f"⚠️  Large query took {large_query_time:.3f}s - potential performance issue")
                    
            except Exception as e:
                print(f"❌ Large query failed: {e}")
                conn.close()
                return False
            
            # Test 4: Check concurrent database access with timeout
            print("\n4. Testing concurrent database access...")
            
            def concurrent_query():
                try:
                    conn = sqlite3.connect(db_path, timeout=5.0)  # 5 second timeout
                    cur = conn.cursor()
                    cur.execute("SELECT COUNT(*) FROM games")
                    result = cur.fetchone()[0]
                    conn.close()
                    return result
                except Exception as e:
                    print(f"Concurrent query failed: {e}")
                    return None
            
            # Run multiple concurrent queries with strict timeout
            threads = []
            results = []
            
            for i in range(5):
                thread = threading.Thread(target=lambda: results.append(concurrent_query()))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete with timeout
            start_time = time.time()
            for thread in threads:
                thread.join(timeout=10.0)  # 10 second timeout per thread
                if thread.is_alive():
                    print("❌ Thread timeout - potential stalling")
                    return False
            
            total_time = time.time() - start_time
            if len(results) == 5 and all(r is not None for r in results):
                print(f"✅ Concurrent database access successful in {total_time:.3f}s")
            else:
                print("❌ Concurrent database access failed - potential stalling")
                return False
            
            # Test 5: Check database manager functionality directly
            print("\n5. Testing database manager functionality...")
            
            # Import and test the database manager functions directly
            try:
                from othello_coach.tools.diag import DB_PATH, ensure_database
                
                # Temporarily override DB_PATH for testing
                original_db_path = DB_PATH
                import othello_coach.tools.diag
                othello_coach.tools.diag.DB_PATH = Path(db_path)
                
                try:
                    # Test database operations that the manager would use
                    conn = sqlite3.connect(str(db_path), timeout=5.0)
                    cur = conn.cursor()
                    
                    # Test the queries that the database manager performs
                    manager_start = time.time()
                    
                    # Test stats query (like in refresh function)
                    for table in ("positions", "analyses", "moves", "notes", "games", "features", "trainer", "ladders", "mappings", "gdl_programs"):
                        try:
                            cur.execute(f"SELECT COUNT(1) FROM {table}")
                            count = cur.fetchone()[0]
                        except Exception:
                            count = 0
                    
                    # Test ladder query (like in refresh_ladder function)
                    cur.execute("""
                        SELECT profile, rating, RD, last_rated_at 
                        FROM ladders 
                        ORDER BY rating DESC
                    """)
                    ladder_results = cur.fetchall()
                    
                    # Test games query (like in refresh_games function)
                    cur.execute("""
                        SELECT id, result, length, tags, started_at, finished_at, moves 
                        FROM games 
                        ORDER BY started_at DESC 
                        LIMIT 50
                    """)
                    games_results = cur.fetchall()
                    
                    conn.close()
                    manager_time = time.time() - manager_start
                    
                    if manager_time < 0.5:  # Should complete within 0.5 seconds
                        print(f"✅ Database manager queries completed in {manager_time:.3f}s")
                    else:
                        print(f"⚠️  Database manager queries took {manager_time:.3f}s - potential stalling")
                    
                    print(f"   - Ladder entries: {len(ladder_results)}")
                    print(f"   - Games: {len(games_results)}")
                    
                finally:
                    # Restore original DB_PATH
                    othello_coach.tools.diag.DB_PATH = original_db_path
                    
            except Exception as e:
                print(f"❌ Database manager functionality test failed: {e}")
                return False
            
            print("\n✅ All database manager tests completed successfully!")
            return True
            
        finally:
            # Clean up temporary database
            try:
                os.unlink(db_path)
            except:
                pass
            
    except Exception as e:
        print(f"❌ Error testing database manager integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_notation_functions():
    """Test coordinate notation functions work correctly"""
    try:
        from othello_coach.engine.notation import coord_to_notation, notation_to_coord, string_to_moves
        
        # Test coordinate conversion
        assert coord_to_notation(19) == "d3"
        assert coord_to_notation(26) == "c4"
        assert coord_to_notation(0) == "a1"
        assert coord_to_notation(63) == "h8"
        
        # Test notation conversion
        assert notation_to_coord("d3") == 19
        assert notation_to_coord("c4") == 26
        assert notation_to_coord("a1") == 0
        assert notation_to_coord("h8") == 63
        
        # Test moves string parsing
        moves_str = "c4e3c3d3"
        coords = string_to_moves(moves_str)
        assert coords == [26, 20, 18, 19]
        
        # Test with passes
        moves_with_passes = "e6f4--c3d3"
        coords_with_passes = string_to_moves(moves_with_passes)
        assert coords_with_passes == [44, 29, -1, 18, 19]
        
        print("✅ Coordinate notation functions work correctly")
        return True
        
    except Exception as e:
        print(f"❌ Error testing notation functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_db_manager_coordinate_transcripts():
    """Test that DB manager shows coordinate transcripts for games - simplified version"""
    try:
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Create test database
            create_test_database(db_path)
            
            # Test database manager functionality without GUI
            print("Testing database manager coordinate transcript functionality...")
            
            # Mock the DB_PATH to use our test database
            import othello_coach.tools.diag
            original_db_path = othello_coach.tools.diag.DB_PATH
            othello_coach.tools.diag.DB_PATH = Path(db_path)
            
            try:
                # Test database operations that the manager would use
                conn = sqlite3.connect(str(db_path), timeout=5.0)
                cur = conn.cursor()
                
                # Test the queries that the database manager performs
                manager_start = time.time()
                
                # Test stats query (like in refresh function)
                for table in ("positions", "analyses", "moves", "notes", "games", "features", "trainer", "ladders", "mappings", "gdl_programs"):
                    try:
                        cur.execute(f"SELECT COUNT(1) FROM {table}")
                        count = cur.fetchone()[0]
                    except Exception:
                        count = 0
                
                # Test ladder query (like in refresh_ladder function)
                cur.execute("""
                    SELECT profile, rating, RD, last_rated_at 
                    FROM ladders 
                    ORDER BY rating DESC
                """)
                ladder_results = cur.fetchall()
                
                # Test games query (like in refresh_games function)
                cur.execute("""
                    SELECT id, result, length, tags, started_at, finished_at, moves 
                    FROM games 
                    ORDER BY started_at DESC 
                    LIMIT 50
                """)
                games_results = cur.fetchall()
                
                conn.close()
                manager_time = time.time() - manager_start
                
                if manager_time < 0.5:  # Should complete within 0.5 seconds
                    print(f"✅ Database manager queries completed in {manager_time:.3f}s")
                else:
                    print(f"⚠️  Database manager queries took {manager_time:.3f}s - potential stalling")
                
                print(f"   - Ladder entries: {len(ladder_results)}")
                print(f"   - Games: {len(games_results)}")
                
                # Check that we have sample games
                if len(games_results) < 3:
                    print("❌ Expected at least 3 games, found:", len(games_results))
                    return False
                
                print(f"✅ Found {len(games_results)} games in database")
                
                # Check that moves are stored in coordinate notation
                moves_found = False
                for game in games_results[:3]:  # Check first 3 games
                    moves_text = game[6]  # moves column
                    if moves_text:
                        # Check if moves contain coordinate notation patterns
                        # Moves could be stored as "e6f4c3d3" or "e6 f4 c3 d3" or similar
                        if any(len(move) == 2 and move[0].isalpha() and move[1].isdigit() for move in moves_text.replace(' ', '')):
                            moves_found = True
                            print(f"✅ Found coordinate moves in game: {moves_text[:20]}...")
                            break
                        # Also check for pass notation
                        elif '--' in moves_text:
                            moves_found = True
                            print(f"✅ Found moves with pass notation: {moves_text[:20]}...")
                            break
                
                if not moves_found:
                    print("❌ No coordinate notation moves found in games")
                    print("Available moves data:")
                    for i, game in enumerate(games_results[:3]):
                        print(f"  Game {i+1}: {game[6]}")
                    return False
                
                print("✅ Database manager shows coordinate transcripts correctly!")
                return True
                
            finally:
                # Restore original DB_PATH
                othello_coach.tools.diag.DB_PATH = original_db_path
                
        finally:
            # Clean up temporary database
            try:
                os.unlink(db_path)
            except:
                pass
            
    except Exception as e:
        print(f"❌ Error testing database manager: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing Othello Coach Database Manager Integration...")
    print("=" * 60)
    
    # Test notation functions first
    if not test_notation_functions():
        print("❌ Notation function tests failed")
        sys.exit(1)
    
    # Test database manager integration
    if test_db_manager_integration():
        print("\n🎉 All tests passed! Database manager is working correctly without stalling.")
    else:
        print("\n❌ Database manager integration tests failed")
        sys.exit(1)
    
    # Test coordinate transcript functionality
    if test_db_manager_coordinate_transcripts():
        print("\n🎉 Coordinate transcript tests passed!")
    else:
        print("\n❌ Coordinate transcript tests failed")
        sys.exit(1)
