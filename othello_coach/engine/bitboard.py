from __future__ import annotations
from dataclasses import dataclass
from typing import Iterator, Tuple
import random

# Board is 8x8, squares numbered 0..63, A1=0 (LSB) to H8=63 (MSB).
# Bitboards: 1 bit per square. We keep black and white bitboards and side-to-move (0=Black,1=White).

# Directions as bit shifts (N=8, S=-8 etc). We will precompute masks for wrap avoidance.
DIRS = (
    8,   # N
    -8,  # S
    1,   # E
    -1,  # W
    9,   # NE
    7,   # NW
    -7,  # SE
    -9,  # SW
)

# File masks to prevent horizontal wrap
FILE_A = 0x0101010101010101
FILE_H = 0x8080808080808080
NOT_FILE_A = ~FILE_A & 0xFFFFFFFFFFFFFFFF
NOT_FILE_H = ~FILE_H & 0xFFFFFFFFFFFFFFFF

EDGE_MASK = 0xFF818181818181FF
CORNER_MASK = (1 << 0) | (1 << 7) | (1 << 56) | (1 << 63)

# Precompute directional masks to block wrapping
DIR_MASKS = {
    1: NOT_FILE_H,
    -1: NOT_FILE_A,
    7: NOT_FILE_A,
    -7: NOT_FILE_H,
    9: NOT_FILE_H,
    -9: NOT_FILE_A,
    8: 0xFFFFFFFFFFFFFFFF,
    -8: 0xFFFFFFFFFFFFFFFF,
}

# Zobrist hashing
random.seed(2025)
ZOBRIST = [[random.getrandbits(64) for _ in range(64)] for _ in range(2)]
ZOBRIST_BLACK_TO_MOVE = random.getrandbits(64)


def popcount(x: int) -> int:
    return x.bit_count()


def shift(bb: int, d: int) -> int:
    if d > 0:
        return (bb << d) & 0xFFFFFFFFFFFFFFFF
    else:
        return (bb >> (-d)) & 0xFFFFFFFFFFFFFFFF


def legal_moves(me: int, opp: int) -> int:
    """Return bitmask of legal moves for side with discs `me` against `opp`."""
    empty = ~(me | opp) & 0xFFFFFFFFFFFFFFFF
    moves = 0
    for d in DIRS:
        mask = DIR_MASKS[d]
        x = shift(me, d) & opp & mask
        x = x & mask
        for _ in range(5):  # max flips in a line before hitting border
            x = shift(x, d) & opp & mask
        # Now gather frontier
        x = shift(me, d) & opp & mask
        while x:
            x2 = shift(x, d) & mask
            captures = x2 & opp
            if not captures:
                break
            x = x2
        # Standard bitboard move-gen trick (faster expanded below)
    # A more direct, standard approach per direction:
    moves = 0
    for d in DIRS:
        mask = DIR_MASKS[d]
        x = shift(me, d) & opp & mask
        acc = 0
        while x:
            acc |= x
            x = shift(x, d) & opp & mask
        m = shift(acc, d) & empty & mask
        moves |= m
    return moves


def flips_for_move(me: int, opp: int, move: int) -> int:
    """Return bitboard of discs to flip if we play `move` (single-bit int set) for `me`."""
    flips = 0
    for d in DIRS:
        mask = DIR_MASKS[d]
        x = 0
        y = shift(move, d) & opp & mask
        while y:
            x |= y
            y = shift(y, d) & opp & mask
        end = shift(x, d) & me & mask
        if end:
            flips |= x
    return flips


def play_move(me: int, opp: int, sq: int) -> Tuple[int, int]:
    move = 1 << sq
    flips = flips_for_move(me, opp, move)
    if flips == 0:
        raise ValueError("Illegal move")
    me2 = me ^ (flips | move)
    opp2 = opp ^ flips
    return me2, opp2


@dataclass(frozen=True)
class Position:
    black: int
    white: int
    stm: int  # 0=Black,1=White

    @staticmethod
    def initial() -> "Position":
        black = (1 << 28) | (1 << 35)  # E4, D5 in 0-index A1=0 -> D5=27? We ensure standard: center
        white = (1 << 27) | (1 << 36)
        return Position(black=black, white=white, stm=0)

    def me_opp(self) -> Tuple[int, int]:
        return (self.black, self.white) if self.stm == 0 else (self.white, self.black)

    def legal_mask(self) -> int:
        me, opp = self.me_opp()
        return legal_moves(me, opp)

    def pass_move(self) -> "Position":
        return Position(self.black, self.white, 1 - self.stm)

    def apply(self, sq: int) -> "Position":
        me, opp = self.me_opp()
        me2, opp2 = play_move(me, opp, sq)
        if self.stm == 0:
            return Position(me2, opp2, 1)
        else:
            return Position(opp2, me2, 1)

    def terminal(self) -> bool:
        if self.legal_mask() != 0:
            return False
        if Position(self.black, self.white, 1 - self.stm).legal_mask() != 0:
            return False
        return True

    def score_disc_diff(self) -> int:
        b = popcount(self.black)
        w = popcount(self.white)
        return b - w  # +ve means Black ahead

    def hash64(self) -> int:
        h = 0
        for i in range(64):
            if (self.black >> i) & 1:
                h ^= ZOBRIST[0][i]
            if (self.white >> i) & 1:
                h ^= ZOBRIST[1][i]
        if self.stm == 0:
            h ^= ZOBRIST_BLACK_TO_MOVE
        return h


