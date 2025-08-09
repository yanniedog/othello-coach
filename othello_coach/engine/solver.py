from __future__ import annotations

from .board import Board, compute_hash
from .movegen_fast import legal_moves_mask
from .board import make_move


def terminal_disc_diff_cp(board: Board) -> int:
    return (board.B.bit_count() - board.W.bit_count()) * 100


def solve_exact(board: Board) -> int:
    mask = legal_moves_mask(board.B, board.W, board.stm)
    if mask == 0:
        # pass move
        new_stm = 1 - board.stm
        b_pass = Board(board.B, board.W, new_stm, board.ply + 1, compute_hash(board.B, board.W, new_stm))
        mask2 = legal_moves_mask(b_pass.B, b_pass.W, b_pass.stm)
        if mask2 == 0:
            return terminal_disc_diff_cp(board)
        return -solve_exact(b_pass)
    best = -1_000_000
    m = mask
    while m:
        lsb = m & -m
        sq = lsb.bit_length() - 1
        m ^= lsb
        b2, _ = make_move(board, sq)
        score = -solve_exact(b2)
        if score > best:
            best = score
    return best
