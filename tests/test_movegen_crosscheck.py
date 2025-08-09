from __future__ import annotations

import random

from othello_coach.engine.board import start_board, make_move, undo_move, compute_hash
from othello_coach.engine.movegen_ref import legal_moves_mask as ref_legal
from othello_coach.engine.movegen_fast import legal_moves_mask as fast_legal


def random_play(board, plies: int = 16):
    b = board
    for _ in range(plies):
        mask = fast_legal(b.B, b.W, b.stm)
        if mask == 0:
            # pass
            b = type(b)(b.B, b.W, 1 - b.stm, b.ply + 1, b.hash)
            continue
        moves = []
        m = mask
        while m:
            lsb = m & -m
            moves.append(lsb.bit_length() - 1)
            m ^= lsb
        sq = random.choice(moves)
        b, _ = make_move(b, sq)
    return b


def test_movegen_match_on_random_positions_and_undo_hash():
    random.seed(0xC0FFEE)
    b = start_board()
    for _ in range(10_000):
        mask_ref = ref_legal(b.B, b.W, b.stm)
        mask_fast = fast_legal(b.B, b.W, b.stm)
        assert mask_ref == mask_fast
        # verify make->undo returns identical board and hash equals recomputed
        m = mask_fast
        while m:
            lsb = m & -m
            sq = lsb.bit_length() - 1
            m ^= lsb
            b2, frame = make_move(b, sq)
            b3 = undo_move(b2, frame)
            assert (b3.B, b3.W, b3.stm, b3.ply) == (b.B, b.W, b.stm, b.ply)
            assert b3.hash == b.hash == compute_hash(b.B, b.W, b.stm)
        b = random_play(b, 1)


