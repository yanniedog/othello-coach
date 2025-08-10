from __future__ import annotations

from .board import NOT_A, NOT_H

# Try to import Rust kernel for acceleration
try:
    import rust_kernel
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

# Directions in deltas: N, S, E, W, NE, NW, SE, SW
DIRS = [8, -8, 1, -1, 9, 7, -7, -9]


def _shift(bb: int, d: int) -> int:
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
    """Get legal moves mask - uses Rust kernel if available for speed"""
    if RUST_AVAILABLE:
        return rust_kernel.legal_mask(B, W, stm)
    
    # Fallback to pure Python implementation
    own, opp = (B, W) if stm == 0 else (W, B)
    empty = ~(B | W) & 0xFFFFFFFFFFFFFFFF
    moves = 0
    # For each direction, expand captures using shift-and-mask trick
    for d in DIRS:
        t = _shift(own, d) & opp
        # Up to 5 additional expansions are sufficient on an 8x8 board
        t |= _shift(t, d) & opp
        t |= _shift(t, d) & opp
        t |= _shift(t, d) & opp
        t |= _shift(t, d) & opp
        t |= _shift(t, d) & opp
        moves |= _shift(t, d) & empty
    return moves


def flip_mask(b: int, w: int, stm: int, sq: int) -> int:
    """Get flip mask for a move - uses Rust kernel if available for speed"""
    if RUST_AVAILABLE:
        return rust_kernel.flip_mask(b, w, stm, sq)
    
    # Fallback to pure Python implementation
    own, opp = (b, w) if stm == 0 else (w, b)
    # Re-traverse each direction from the move square to compute flips
    m = 1 << sq
    flips = 0
    for d in DIRS:
        run = 0
        cur = _shift(m, d)
        while cur and (cur & opp):
            run |= cur
            cur = _shift(cur, d)
        if run and (cur & own):
            flips |= run
    return flips


# Export with expected name for tests
generate_legal_mask = legal_moves_mask
generate_flip_mask = flip_mask