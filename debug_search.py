#!/usr/bin/env python3
"""Debug search function to see why it's failing"""

import sys
sys.path.insert(0, '.')

from othello_coach.engine.board import start_board
from othello_coach.engine.search import search_position, SearchLimits
from othello_coach.engine.movegen_fast import legal_moves_mask

def debug_search():
    """Debug search function"""
    print("🔍 Debugging search function...")
    
    # Start with initial board
    board = start_board()
    print(f"Board: B={bin(board.B)}, W={bin(board.W)}, stm={board.stm}")
    
    # Check legal moves
    legal = legal_moves_mask(board.B, board.W, board.stm)
    print(f"Legal moves: {bin(legal)}")
    
    # Try search with different limits
    limits = SearchLimits(max_depth=2, time_ms=1000)
    print(f"Search limits: {limits}")
    
    try:
        result = search_position(board, limits)
        print(f"Search result: {result}")
        if result:
            print(f"  - Best move: {result.best_move}")
            print(f"  - Score: {result.score_cp}")
            print(f"  - Depth: {result.depth}")
            print(f"  - PV: {result.pv}")
            print(f"  - Nodes: {result.nodes}")
            print(f"  - Time: {result.time_ms}ms")
        else:
            print("❌ Search returned None!")
    except Exception as e:
        print(f"❌ Search failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_search()
