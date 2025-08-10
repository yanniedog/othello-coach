#!/usr/bin/env python3
"""Quick GUI functionality test"""

import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing basic imports...")
    
    try:
        from othello_coach.ui.main_window import MainWindow
        print("✅ MainWindow imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import MainWindow: {e}")
        return False
    
    try:
        from othello_coach.ui.board_widget import BoardWidget
        print("✅ BoardWidget imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import BoardWidget: {e}")
        return False
    
    try:
        from othello_coach.engine.board import start_board
        print("✅ Engine board imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import engine board: {e}")
        return False
    
    try:
        from othello_coach.insights.features import extract_features
        print("✅ Insights features imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import insights features: {e}")
        return False
    
    try:
        from othello_coach.trees.builder import build_tree
        print("✅ Tree builder imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import tree builder: {e}")
        return False
    
    try:
        from othello_coach.trainer.trainer import Trainer
        print("✅ Trainer imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import trainer: {e}")
        return False
    
    try:
        from othello_coach.gauntlet.gauntlet import GauntletRunner
        print("✅ Gauntlet runner imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import gauntlet runner: {e}")
        return False
    
    try:
        from othello_coach.novelty.radar import NoveltyRadar
        print("✅ Novelty radar imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import novelty radar: {e}")
        return False
    
    try:
        from othello_coach.api.server import APIServer
        print("✅ API server imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import API server: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Test basic functionality without GUI"""
    print("\n🧪 Testing basic functionality...")
    
    try:
        from othello_coach.engine.board import start_board, legal_moves_mask
        board = start_board()
        print("✅ Board creation successful")
        
        legal_moves = legal_moves_mask(board)
        move_count = bin(legal_moves).count('1')
        print(f"✅ Legal moves: {move_count} moves available")
        
        if move_count > 0:
            # Test a move
            from othello_coach.engine.board import make_move
            # Find first legal move
            for i in range(64):
                if legal_moves & (1 << i):
                    move = i
                    break
            
            new_board, frame = make_move(board, move)
            print(f"✅ Move {move} executed successfully")
            
            # Test undo
            from othello_coach.engine.board import undo_move
            restored_board = undo_move(new_board, frame)
            print("✅ Move undo successful")
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False
    
    return True

def test_config_loading():
    """Test configuration loading"""
    print("\n🧪 Testing configuration loading...")
    
    try:
        from othello_coach.tools.api_cli import load_config
        # Try to load config, but don't fail if file doesn't exist
        try:
            config = load_config()
            print("✅ Configuration loaded successfully")
            
            # Check required sections
            required_sections = ['feature_flags', 'api', 'trainer', 'gauntlet']
            for section in required_sections:
                if section in config:
                    print(f"✅ {section} section present")
                else:
                    print(f"⚠️  {section} section missing")
        except FileNotFoundError:
            print("⚠️  Config file not found (this is normal for first run)")
            print("✅ Configuration loading mechanism works")
        
    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False
    
    return True

def main():
    """Run all quick tests"""
    print("🚀 Quick GUI Functionality Test")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_basic_imports():
        success = False
    
    # Test basic functionality
    if not test_basic_functionality():
        success = False
    
    # Test config loading
    if not test_config_loading():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All quick tests passed! Ready for comprehensive testing.")
        print("Run: python run_gui_tests.py")
    else:
        print("❌ Some quick tests failed. Fix issues before comprehensive testing.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
