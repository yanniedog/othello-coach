from __future__ import annotations

from .board import NOT_A, NOT_H

DIRS = [8, -8, 1, -1, 9, 7, -7, -9]


def shift(bb: int, d: int) -> int:
    if d == 8:
        return (bb << 8) & 0xFFFFFFFFFFFFFFFF
    if d == -8:
        return (bb >> 8) & 0xFFFFFFFFFFFFFFFF
    if d == 1:
        return (bb << 1) & NOT_A & 0xFFFFFFFFFFFFFFFF
    if d == -1:
        return (bb >> 1) & NOT_H & 0xFFFFFFFFFFFFFFFF
    if d == 9:
        return (bb << 9) & NOT_A & 0xFFFFFFFFFFFFFFFF
    if d == 7:
        return (bb << 7) & NOT_H & 0xFFFFFFFFFFFFFFFF
    if d == -7:
        return (bb >> 7) & NOT_A & 0xFFFFFFFFFFFFFFFF
    if d == -9:
        return (bb >> 9) & NOT_H & 0xFFFFFFFFFFFFFFFF
    raise ValueError("bad dir")


def legal_moves_mask(B: int, W: int, stm: int) -> int:
    own, opp = (B, W) if stm == 0 else (W, B)
    empty = ~(B | W) & 0xFFFFFFFFFFFFFFFF
    moves = 0
    empties = empty
    while empties:
        lsb = empties & -empties
        sq = lsb.bit_length() - 1
        empties ^= lsb
        m = 1 << sq
        for d in DIRS:
            cur = shift(m, d)
            seen = 0
            while cur and (cur & opp):
                seen |= cur
                cur = shift(cur, d)
            if seen and (cur & own):
                moves |= m
                break
    return moves


def flip_mask_for_move(own: int, opp: int, sq: int) -> int:
    m = 1 << sq
    flips = 0
    for d in DIRS:
        run = 0
        cur = shift(m, d)
        while cur and (cur & opp):
            run |= cur
            cur = shift(cur, d)
        if run and (cur & own):
            flips |= run
    return flips


# Export with expected name for tests
generate_legal_mask = legal_moves_mask
generate_flip_mask = flip_mask_for_move