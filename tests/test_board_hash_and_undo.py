from __future__ import annotations

from othello_coach.engine.board import start_board, make_move, undo_move, compute_hash


def test_make_undo_restores_board_and_hash():
    b0 = start_board()
    # play first legal move
    from othello_coach.engine.movegen_fast import legal_moves_mask

    mask = legal_moves_mask(b0.B, b0.W, b0.stm)
    assert mask
    sq = (mask & -mask).bit_length() - 1
    b1, frame = make_move(b0, sq)
    b2 = undo_move(b1, frame)
    assert b2.B == b0.B and b2.W == b0.W and b2.stm == b0.stm and b2.ply == b0.ply
    assert b2.hash == b0.hash == compute_hash(b0.B, b0.W, b0.stm)


