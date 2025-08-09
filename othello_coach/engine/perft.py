from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, List
from importlib import resources
import json

from .board import Board, start_board, make_move
from .movegen_fast import legal_moves_mask


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    total = 0
    mask = legal_moves_mask(board.B, board.W, board.stm)
    m = mask
    while m:
        lsb = m & -m
        sq = lsb.bit_length() - 1
        m ^= lsb
        b2, _ = make_move(board, sq)
        total += perft(b2, depth - 1)
    return total


FILES = "abcdefgh"


def coord_to_sq(coord: str) -> int:
    if len(coord) != 2:
        raise ValueError(f"bad coord: {coord}")
    file_c = coord[0].lower()
    rank_c = coord[1]
    x = FILES.find(file_c)
    y = int(rank_c) - 1
    if x < 0 or not (0 <= y < 8):
        raise ValueError(f"bad coord: {coord}")
    return x + 8 * y


def play_moves(board: Optional[Board], moves: Iterable[str]) -> Board:
    b = start_board() if board is None else board
    for mv in moves:
        sq = coord_to_sq(mv)
        b, _ = make_move(b, sq)
    return b


def load_perft_pack() -> List[List[str]]:
    pkg = resources.files("othello_coach.engine").joinpath("perft_pack.json")
    with pkg.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("positions", [])


