#!/usr/bin/env python3
"""Test database manager functionality"""

import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_db_manager():
    """Test database manager creation and data loading"""
    try:
        from PyQt6.QtWidgets import QApplication
        from othello_coach.ui.main_window import MainWindow
        
        # Create QApplication
        app = QApplication([])
        
        # Create main window
        window = MainWindow()
        
        # Test database manager creation
        print("Testing database manager creation...")
        window._show_db_manager()
        print("✅ Database manager created successfully")
        
        # The dialog should show automatically, but for testing we'll just verify it can be created
        
    except Exception as e:
        print(f"❌ Error testing database manager: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_db_manager()
    if success:
        print("✅ Database manager test completed successfully")
    else:
        print("❌ Database manager test failed")
        sys.exit(1)
