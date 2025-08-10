#!/usr/bin/env python3
"""Test script for evaluation function"""

from othello_coach.engine.board import start_board, make_move
from othello_coach.engine.movegen_ref import legal_moves_mask
from othello_coach.engine.eval import evaluate_position

def test_evaluation():
    """Test the evaluation function with a few moves"""
    print("Testing evaluation function...")
    
    # Start with initial board
    board = start_board()
    print(f"Initial position - Black to move")
    print(f"Black discs: {board.B.bit_count()}, White discs: {board.W.bit_count()}")
    
    # Evaluate initial position
    eval_score = evaluate_position(board)
    print(f"Initial evaluation: {eval_score:+}")
    
    # Make a few moves and evaluate
    for move_num in range(1, 6):
        legal = legal_moves_mask(board.B, board.W, board.stm)
        if legal == 0:
            print("No legal moves available")
            break
            
        # Take first legal move
        moves = []
        m = legal
        while m:
            lsb = m & -m
            moves.append(lsb.bit_length() - 1)
            m ^= lsb
            
        if moves:
            move = moves[0]
            board, _ = make_move(board, move)
            eval_score = evaluate_position(board)
            player = "Black" if board.stm == 0 else "White"
            print(f"Move {move_num}: {player} to move, Evaluation: {eval_score:+}")
    
    print("Evaluation test completed!")

if __name__ == "__main__":
    test_evaluation()
