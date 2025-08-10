#!/usr/bin/env python3
"""Test script for the main window with advantage graph integration"""

import sys
from PyQt6.QtWidgets import QApplication

def test_main_window_creation():
    """Test that the main window can be created with advantage graph"""
    try:
        from othello_coach.ui.main_window import MainWindow
        print("✓ MainWindow import successful")
        
        # Create application
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Try to create main window
        window = MainWindow()
        print("✓ MainWindow creation successful")
        
        # Check if advantage graph exists
        if hasattr(window, 'advantage_graph') and window.advantage_graph:
            print("✓ Advantage graph widget found")
        else:
            print("✗ Advantage graph widget not found")
            return False
            
        # Check if it's properly connected
        if hasattr(window, '_on_game_state_changed'):
            print("✓ Game state change handler found")
        else:
            print("✗ Game state change handler not found")
            return False
            
        print("✓ All tests passed - advantage graph integration successful")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_main_window_creation()
    sys.exit(0 if success else 1)
