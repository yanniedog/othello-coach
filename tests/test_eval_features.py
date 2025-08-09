from othello_coach.engine.board import start_board, make_move
from othello_coach.engine.eval import evaluate
from othello_coach.engine.movegen_fast import legal_moves_mask


def test_corner_improves_eval():
    b = start_board()
    # Choose the best immediate move by eval to get a reasonable midgame-ish position
    mask = legal_moves_mask(b.B, b.W, b.stm)
    best_score = -10_000
    best_b = None
    m = mask
    while m:
        lsb = m & -m
        sq = lsb.bit_length() - 1
        m ^= lsb
        b2, _ = make_move(b, sq)
        s = evaluate(b2)
        if s > best_score:
            best_score = s
            best_b = b2
    assert best_b is not None
    # If a corner is legal now, ensure it is not heavily penalised vs a non-corner
    cm = legal_moves_mask(best_b.B, best_b.W, best_b.stm)
    corners = (1 << 0) | (1 << 7) | (1 << 56) | (1 << 63)
    if cm & corners:
        corner_moves = cm & corners
        corner_sq = (corner_moves & -corner_moves).bit_length() - 1
        b_corner, _ = make_move(best_b, corner_sq)
        s_corner = evaluate(b_corner)
        non = cm & ~corners
        if non:
            non_sq = (non & -non).bit_length() - 1
            b_non, _ = make_move(best_b, non_sq)
            s_non = evaluate(b_non)
            assert s_corner >= s_non - 10

