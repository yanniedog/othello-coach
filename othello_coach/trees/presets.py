from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from othello_coach.engine.board import Board
from othello_coach.engine.movegen_fast import legal_moves_mask


@dataclass
class Preset:
    name: str
    scorer: Callable[[Board], float]


def _score_side(board: Board) -> float:
    mask_stm = legal_moves_mask(board.B, board.W, board.stm).bit_count()
    mask_opp = legal_moves_mask(board.B, board.W, 1 - board.stm).bit_count()
    return float(mask_stm - mask_opp)


def _min_opp_mob(board: Board) -> float:
    return float(-legal_moves_mask(board.B, board.W, 1 - board.stm).bit_count())


def _early_corner(board: Board) -> float:
    corners = (1 << 0) | (1 << 7) | (1 << 56) | (1 << 63)
    return 500.0 if (legal_moves_mask(board.B, board.W, board.stm) & corners) else 0.0


def get_preset(name: str) -> Preset:
    if name == "score_side":
        return Preset(name, _score_side)
    if name == "min_opp_mob":
        return Preset(name, _min_opp_mob)
    if name == "early_corner":
        return Preset(name, _early_corner)
    return Preset(name, _score_side)
