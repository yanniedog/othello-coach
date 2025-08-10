#!/usr/bin/env python3
"""Debug script to test why gauntlet games are ending prematurely"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from othello_coach.engine.board import Board
from othello_coach.engine.movegen_fast import generate_legal_mask
from othello_coach.engine.strength import get_strength_profile
from othello_coach.engine.search import search_position, SearchLimits
from othello_coach.engine.board import make_move

def debug_single_move():
    """Test a single move to see what's happening"""
    print("🧪 Debugging single move...")
    
    # Start with initial board
    board = Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=0)
    print(f"Initial board - Black's turn: {board.stm == 0}")
    print(f"Black pieces: {bin(board.B).count('1')}")
    print(f"White pieces: {bin(board.W).count('1')}")
    
    # Check legal moves
    legal_mask = generate_legal_mask(board.B, board.W, board.stm)
    legal_moves = []
    for sq in range(64):
        if legal_mask & (1 << sq):
            legal_moves.append(sq)
    
    print(f"Legal moves for Black: {legal_moves}")
    print(f"Number of legal moves: {len(legal_moves)}")
    
    if not legal_moves:
        print("❌ No legal moves found!")
        return
    
    # Try to get a move from the engine
    strength = get_strength_profile("elo_400")
    print(f"Using strength profile: {strength}")
    
    limits = SearchLimits(
        max_depth=strength.depth,
        time_ms=strength.soft_time_ms
    )
    
    print("🔍 Searching for move...")
    result = search_position(board, limits)
    
    if not result:
        print("❌ Search returned no result")
        return
    
    if not result.pv:
        print("❌ Search result has no PV")
        return
    
    print(f"✅ Search successful: {result}")
    print(f"Best move: {result.pv[0]}")
    print(f"Score: {result.score}")
    
    # Try to make the move
    try:
        new_board, _ = make_move(board, result.pv[0])
        print(f"✅ Move successful")
        print(f"New board - Black's turn: {new_board.stm == 0}")
        print(f"Black pieces: {bin(new_board.B).count('1')}")
        print(f"White pieces: {bin(new_board.W).count('1')}")
        print(f"Ply: {new_board.ply}")
        
        # Check legal moves for next player
        next_legal_mask = generate_legal_mask(new_board.B, new_board.W, new_board.stm)
        next_legal_moves = []
        for sq in range(64):
            if next_legal_mask & (1 << sq):
                next_legal_moves.append(sq)
        
        print(f"Legal moves for next player: {next_legal_moves}")
        print(f"Number of legal moves: {len(next_legal_moves)}")
        
    except Exception as e:
        print(f"❌ Move failed: {e}")
        import traceback
        traceback.print_exc()

def debug_engine_imports():
    """Check if all engine components can be imported"""
    print("🔍 Checking engine imports...")
    
    try:
        from othello_coach.engine.board import Board
        print("✅ Board imported")
    except Exception as e:
        print(f"❌ Board import failed: {e}")
    
    try:
        from othello_coach.engine.movegen_fast import generate_legal_mask
        print("✅ Movegen imported")
    except Exception as e:
        print(f"❌ Movegen import failed: {e}")
    
    try:
        from othello_coach.engine.search import search_position, SearchLimits
        print("✅ Search imported")
    except Exception as e:
        print(f"❌ Search import failed: {e}")
    
    try:
        from othello_coach.engine.strength import get_strength_profile
        print("✅ Strength imported")
    except Exception as e:
        print(f"❌ Strength import failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting gauntlet move debug...")
    debug_engine_imports()
    print()
    debug_single_move()
