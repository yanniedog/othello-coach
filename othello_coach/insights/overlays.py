from __future__ import annotations

from typing import Dict, List, Tuple

from othello_coach.engine.board import Board, make_move
from othello_coach.engine.movegen_fast import legal_moves_mask
from .features import extract_features


def mobility_heat(board: Board) -> Dict[int, int]:
    mask = legal_moves_mask(board.B, board.W, board.stm)
    moves = []
    m = mask
    while m:
        lsb = m & -m
        moves.append(lsb.bit_length() - 1)
        m ^= lsb
    if len(moves) > 10:
        moves = moves[:3]
    heat = {}
    for sq in moves:
        b2, _ = make_move(board, sq)
        feats = extract_features(b2)
        heat[sq] = feats["mobility_stm"]
    return heat


def stability_heat(board: Board) -> Dict[int, int]:
    mask = legal_moves_mask(board.B, board.W, board.stm)
    heat: Dict[int, int] = {}
    m = mask
    count = 0
    while m and count < 10:
        lsb = m & -m
        sq = lsb.bit_length() - 1
        m ^= lsb
        count += 1
        b2, _ = make_move(board, sq)
        feats = extract_features(b2)
        heat[sq] = feats["stability_stm"]
    return heat


def parity_map(board: Board) -> Dict[str, List[int]]:
    """Compute a parity map of empty regions and highlight must-move borders.

    Returns a dict with keys:
    - odd: list of empty squares in odd regions
    - even: list of empty squares in even regions
    - must_move_border: list of empty squares on borders of large odd regions
    """
    empties_mask = ~(board.B | board.W) & 0xFFFFFFFFFFFFFFFF
    empties: List[int] = []
    e = empties_mask
    while e:
        lsb = e & -e
        empties.append(lsb.bit_length() - 1)
        e ^= lsb

    def neighbours4(sq: int) -> List[int]:
        r, f = divmod(sq, 8)
        res: List[int] = []
        if r > 0:
            res.append(sq - 8)
        if r < 7:
            res.append(sq + 8)
        if f > 0:
            res.append(sq - 1)
        if f < 7:
            res.append(sq + 1)
        return res

    odd_squares: List[int] = []
    even_squares: List[int] = []
    must_move_border: List[int] = []
    seen = set()
    for s in empties:
        if s in seen:
            continue
        # BFS region
        region: List[int] = []
        q = [s]
        seen.add(s)
        while q:
            cur = q.pop()
            region.append(cur)
            for nb in neighbours4(cur):
                if nb not in seen and ((empties_mask >> nb) & 1):
                    seen.add(nb)
                    q.append(nb)
        target = odd_squares if (len(region) % 2 == 1) else even_squares
        target.extend(region)
        # Mark border for large odd regions (size>=5)
        if len(region) % 2 == 1 and len(region) >= 5:
            for sq in region:
                # Border squares adjacent to opponent discs are more urgent
                adj_opponent = 0
                for nb in neighbours4(sq):
                    bit = 1 << nb
                    if board.stm == 0:
                        if board.W & bit:
                            adj_opponent += 1
                    else:
                        if board.B & bit:
                            adj_opponent += 1
                if adj_opponent >= 2:
                    must_move_border.append(sq)
    return {"odd": odd_squares, "even": even_squares, "must_move_border": must_move_border}


def corner_tension(board: Board) -> List[Tuple[int, int, str]]:
    """Return arrows marking squares that open/close a corner within 2 plies.

    Each entry is (from_sq, corner_sq, kind) where kind is "opens" if the move
    allows opponent to take a corner next, or "secures" if it enables current
    side to secure a corner within 2 plies (simple approximation).
    """
    corners = [0, 7, 56, 63]
    mask = legal_moves_mask(board.B, board.W, board.stm)
    # Safeguard: if many legal moves, only consider top-3 by resulting mobility
    candidates: List[int] = []
    m = mask
    while m:
        lsb = m & -m
        candidates.append(lsb.bit_length() - 1)
        m ^= lsb
    if len(candidates) > 10:
        scored: List[Tuple[int, int]] = []
        for sq in candidates:
            b2, _ = make_move(board, sq)
            mob = legal_moves_mask(b2.B, b2.W, b2.stm).bit_count()
            scored.append((mob, sq))
        scored.sort(reverse=True)
        candidates = [sq for _, sq in scored[:3]]

    arrows: List[Tuple[int, int, str]] = []
    for sq in candidates:
        b2, _ = make_move(board, sq)
        opp_moves = legal_moves_mask(b2.B, b2.W, b2.stm)
        for c in corners:
            if opp_moves & (1 << c):
                arrows.append((sq, c, "opens"))
        # If our side can get a corner on the subsequent reply (very rough):
        # simulate one opponent pass if no moves to check our immediate corners
        if opp_moves == 0:
            b3 = Board(b2.B, b2.W, 1 - b2.stm, b2.ply + 1, board.hash)
        else:
            # pick an arbitrary opponent move with minimal mobility for us
            best_reply = None
            best_mob = 1 << 30
            mm = opp_moves
            while mm:
                lsb2 = mm & -mm
                r = lsb2.bit_length() - 1
                mm ^= lsb2
                bb, _ = make_move(b2, r)
                mob = legal_moves_mask(bb.B, bb.W, bb.stm).bit_count()
                if mob < best_mob:
                    best_mob = mob
                    best_reply = bb
            b3 = best_reply if best_reply is not None else b2
        if b3 is not None:
            our_moves = legal_moves_mask(b3.B, b3.W, b3.stm)
            for c in corners:
                if our_moves & (1 << c):
                    arrows.append((sq, c, "secures"))
    return arrows