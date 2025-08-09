from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

# Masks
NOT_A = 0xfefefefefefefefe
NOT_H = 0x7f7f7f7f7f7f7f7f

# Zobrist (deterministic)
_Z_SEED = 0x9e3779b97f4a7c15
_Z_KEYS = [[0] * 64 for _ in range(2)]
_Z_STM = 0


def _splitmix64(x: int) -> int:
    x = (x + 0x9e3779b97f4a7c15) & 0xFFFFFFFFFFFFFFFF
    z = x
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9 & 0xFFFFFFFFFFFFFFFF
    z = (z ^ (z >> 27)) * 0x94d049bb133111eb & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)


seed = _Z_SEED
for c in range(2):
    for i in range(64):
        seed = _splitmix64(seed)
        _Z_KEYS[c][i] = seed
seed = _splitmix64(seed)
_Z_STM = seed


@dataclass
class Board:
    B: int
    W: int
    stm: int  # 0 black, 1 white
    ply: int
    hash: int


def start_board() -> Board:
    B = (1 << 28) | (1 << 35)
    W = (1 << 27) | (1 << 36)
    stm = 0
    ply = 0
    h = compute_hash(B, W, stm)
    return Board(B, W, stm, ply, h)


def compute_hash(B: int, W: int, stm: int) -> int:
    h = 0
    for i in range(64):
        bit = 1 << i
        if B & bit:
            h ^= _Z_KEYS[0][i]
        if W & bit:
            h ^= _Z_KEYS[1][i]
    if stm:
        h ^= _Z_STM
    return h & 0xFFFFFFFFFFFFFFFF


@dataclass
class StackFrame:
    move_sq: int
    flipped: int
    prev_hash: int
    prev_stm: int
    prev_ply: int


def legal_moves_mask(board: Board) -> int:
    from .movegen_fast import legal_moves_mask as fast

    return fast(board.B, board.W, board.stm)


def make_move(board: Board, sq: int) -> Tuple[Board, StackFrame]:
    from .movegen_fast import flip_mask_for_move

    mask = 1 << sq
    legal = legal_moves_mask(board)
    if not (mask & legal):
        raise ValueError("illegal move")
    own = board.B if board.stm == 0 else board.W
    opp = board.W if board.stm == 0 else board.B
    flips = flip_mask_for_move(own, opp, sq)
    if flips == 0:
        raise ValueError("illegal move (no flips)")

    prev = StackFrame(sq, flips, board.hash, board.stm, board.ply)

    # Incremental Zobrist update
    h = board.hash
    # remove stm
    if board.stm:
        h ^= _Z_STM
    # place piece at sq and flip captured discs
    color_idx = board.stm  # 0 for B, 1 for W
    other_idx = 1 - color_idx
    # place new piece
    h ^= _Z_KEYS[color_idx][sq]
    # flip discs: remove from opp, add to own
    f = flips
    while f:
        lsb = f & -f
        i = lsb.bit_length() - 1
        h ^= _Z_KEYS[color_idx][i]
        h ^= _Z_KEYS[other_idx][i]
        f ^= lsb

    own |= mask | flips
    opp &= ~flips & ((1 << 64) - 1)

    if board.stm == 0:
        B, W = own, opp
    else:
        W, B = own, opp

    stm = 1 - board.stm
    ply = board.ply + 1
    # add stm for next player
    if stm:
        h ^= _Z_STM
    return Board(B, W, stm, ply, h & 0xFFFFFFFFFFFFFFFF), prev


def undo_move(board: Board, frame: StackFrame) -> Board:
    # Reconstruct prior board using stored mask
    # 'own' refers to the side that made the move (prev_stm)
    own = board.B if frame.prev_stm == 0 else board.W
    opp = board.W if frame.prev_stm == 0 else board.B
    mask = 1 << frame.move_sq
    own &= ~mask & ((1 << 64) - 1)
    own &= ~frame.flipped & ((1 << 64) - 1)
    opp |= frame.flipped
    if frame.prev_stm == 0:
        B, W = own, opp
    else:
        W, B = own, opp
    # Use stored prev_hash which was exact prior to make_move
    return Board(B, W, frame.prev_stm, frame.prev_ply, frame.prev_hash)
