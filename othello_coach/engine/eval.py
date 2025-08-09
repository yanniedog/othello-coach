from __future__ import annotations

from .board import Board
from othello_coach.insights.features import extract_features

WEIGHTS = {
    "mobility": 80,
    "potential_mobility": 20,
    "corner_delta": 900,
    "x_c_penalty": -140,
    "frontier": -18,
    "disc_diff": 2,  # scaled by (1 - phase)
    "parity": 40,
    "stability": 25,
}


def evaluate(board: Board) -> int:
    feats = extract_features(board)
    empties = 64 - (board.B | board.W).bit_count()
    phase = empties / 64.0
    score = 0
    score += WEIGHTS["mobility"] * (feats["mobility_stm"] - feats["mobility_opp"])
    score += WEIGHTS["potential_mobility"] * (feats["pot_mob_stm"] - feats["pot_mob_opp"])
    score += WEIGHTS["corner_delta"] * (feats["corners_stm"] - feats["corners_opp"])
    score += WEIGHTS["x_c_penalty"] * feats["x_c_risk"]
    score += WEIGHTS["frontier"] * (feats["frontier_stm"] - feats["frontier_opp"])
    score += int(WEIGHTS["disc_diff"] * (1 - phase) * (feats["disc_stm"] - feats["disc_opp"]))
    score += WEIGHTS["parity"] * feats["parity_pressure"]
    score += WEIGHTS["stability"] * (feats["stability_stm"] - feats["stability_opp"])
    return int(score)
