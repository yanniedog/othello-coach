from __future__ import annotations

from typing import Dict, List

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