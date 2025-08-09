from __future__ import annotations

import os

from .board import Board, compute_hash
from .movegen_fast import legal_moves_mask
from .board import make_move


def terminal_disc_diff_cp(board: Board) -> int:
    return (board.B.bit_count() - board.W.bit_count()) * 100


def solve_exact(board: Board, max_empties: int = 12) -> int:
    """Exact solver with optional Rust acceleration.

    To prevent UI stalls in CPU vs CPU mode, Rust exact solving is disabled by default
    unless environment variable `OTHELLO_COACH_RUST_EXACT=1` is set. Python fallback
    remains deterministic and fast enough for ≤12 empties in GUI usage.
    """
    empties = 64 - (board.B.bit_count() + board.W.bit_count())
    
    # Optional Rust acceleration (off by default to avoid stalls)
    use_rust = os.environ.get("OTHELLO_COACH_RUST_EXACT", "0") == "1"
    if use_rust:
        try:
            import rust_kernel
            # Keep a conservative limit to bound runtime
            rust_max_empties = 12
            if empties <= rust_max_empties:
                return rust_kernel.exact_solver(board.B, board.W, board.stm, empties, 64)
        except (ImportError, AttributeError):
            pass
    
    # Fall back to Python solver
    if empties > max_empties:
        # Use heuristic evaluation for positions with too many empties
        from .eval import evaluate_position
        return evaluate_position(board)
    
    return _python_exact_solver(board)


def _python_exact_solver(board: Board) -> int:
    """Python implementation of exact solver"""
    mask = legal_moves_mask(board.B, board.W, board.stm)
    if mask == 0:
        # pass move
        new_stm = 1 - board.stm
        b_pass = Board(board.B, board.W, new_stm, board.ply + 1, compute_hash(board.B, board.W, new_stm))
        mask2 = legal_moves_mask(b_pass.B, b_pass.W, b_pass.stm)
        if mask2 == 0:
            return terminal_disc_diff_cp(board)
        return -_python_exact_solver(b_pass)
    
    best = -1_000_000
    m = mask
    while m:
        lsb = m & -m
        sq = lsb.bit_length() - 1
        m ^= lsb
        b2, _ = make_move(board, sq)
        score = -_python_exact_solver(b2)
        if score > best:
            best = score
    return best


def get_solver_threshold(config: dict = None) -> int:
    """Get current solver threshold based on configuration"""
    if config is None:
        # Conservative default: avoid calling exact solver too early to prevent UI stalls
        # regardless of acceleration availability.
        return 12
    
    accel_enabled = config.get('engine', {}).get('accel_enabled', True)
    
    # Check if acceleration is actually available
    try:
        import rust_kernel
        rust_available = True
    except ImportError:
        rust_available = False
        accel_enabled = False
    
    if accel_enabled and rust_available:
        return config.get('engine', {}).get('endgame_exact_empties', 12)
    else:
        return 12  # Python solver limit
