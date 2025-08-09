from othello_coach.engine.board import start_board
from othello_coach.insights.rationale import explain_move
from othello_coach.engine.movegen_fast import legal_moves_mask


def test_rationale_present_for_most_moves():
    b = start_board()
    mask = legal_moves_mask(b.B, b.W, b.stm)
    m = mask
    num = 0
    with_reason = 0
    while m:
        lsb = m & -m
        sq = lsb.bit_length() - 1
        m ^= lsb
        r = explain_move(b, sq)
        num += 1
        if r:
            with_reason += 1
    assert with_reason / max(1, num) >= 0.75

