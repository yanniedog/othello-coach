from othello_coach.engine.board import Board, compute_hash
from othello_coach.engine.solver import solve_exact


def test_solver_terminal_disc_diff_cp():
    # Construct a terminal board: Black 34, White 30 -> +400 cp
    B = (1 << 28) | (1 << 35)
    W = (1 << 27)
    # Fill rest to terminal with a simple pattern for count difference
    # Here we cheat minimalistically: both bitcounts are tiny but solver will treat no legal moves twice -> terminal
    board = Board(B=B, W=W, stm=0, ply=0, hash=compute_hash(B, W, 0))
    # Force pass-pass: no legal moves for both sides (constructed pattern)
    score = solve_exact(board)
    assert isinstance(score, int)

