#!/usr/bin/env python3
"""Test database manager functionality with coordinate transcript display"""

import sys
import os
import sqlite3
import tempfile
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

def test_db_manager_coordinate_transcripts():
    """Test that DB manager shows coordinate transcripts for games"""
    try:
        from PyQt6.QtWidgets import QApplication, QTableWidgetItem
        from othello_coach.ui.main_window import MainWindow
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp_file:
            db_path = tmp_file.name
        
        try:
            # Create test database
            create_test_database(db_path)
            
            # Mock the DB_PATH to use our test database
            import othello_coach.tools.diag
            original_db_path = othello_coach.tools.diag.DB_PATH
            othello_coach.tools.diag.DB_PATH = Path(db_path)
            
            try:
                # Create QApplication
                app = QApplication([])
                
                # Create main window
                window = MainWindow()
                
                # Test database manager creation
                print("Testing database manager creation...")
                
                # Show the dialog
                window._show_db_manager()
                
                # Find the dialog that was created
                dialog = None
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'windowTitle') and widget.windowTitle() == "Database Manager":
                        dialog = widget
                        break
                
                if not dialog:
                    print("❌ Database manager dialog not found")
                    return False
                
                print("✅ Database manager dialog created successfully")
                
                # Find the games table
                games_table = None
                for child in dialog.findChildren(QTableWidgetItem):
                    if hasattr(child, 'tableWidget'):
                        table = child.tableWidget()
                        if table and table.columnCount() == 7:  # Should have 7 columns now
                            games_table = table
                            break
                
                if not games_table:
                    print("❌ Could not find games table in dialog")
                    return False
                
                print("✅ Found games table with 7 columns")
                
                # Check that we have the moves column
                header_item = games_table.horizontalHeaderItem(6)
                if not header_item or header_item.text() != "Moves":
                    print("❌ Moves column header not found or incorrect")
                    return False
                
                print("✅ Moves column header found")
                
                # Check that we have sample games
                if games_table.rowCount() < 3:
                    print("❌ Expected at least 3 games, found:", games_table.rowCount())
                    return False
                
                print(f"✅ Found {games_table.rowCount()} games in table")
                
                # Check that moves are displayed in coordinate notation
                moves_found = False
                for row in range(min(3, games_table.rowCount())):
                    moves_item = games_table.item(row, 6)
                    if moves_item and moves_item.text():
                        moves_text = moves_item.text()
                        # Should contain coordinate notation like "e6 f4 c3"
                        if any(len(move) == 2 and move[0].isalpha() and move[1].isdigit() for move in moves_text.split()):
                            moves_found = True
                            print(f"✅ Found coordinate moves in row {row}: {moves_text}")
                            break
                
                if not moves_found:
                    print("❌ No coordinate notation moves found in games table")
                    return False
                
                print("✅ Database manager shows coordinate transcripts correctly!")
                
                # Close the dialog
                dialog.accept()
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

if __name__ == "__main__":
    print("Testing Othello Coach Database Manager...")
    print("=" * 50)
    
    # Test notation functions first
    if not test_notation_functions():
        print("❌ Notation function tests failed")
        sys.exit(1)
    
    # Test DB manager
    if test_db_manager_coordinate_transcripts():
        print("✅ All tests passed!")
    else:
        print("❌ Database manager tests failed")
        sys.exit(1)
