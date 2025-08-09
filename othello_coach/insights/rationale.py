from __future__ import annotations

from typing import Dict, List, Tuple

from .features import extract_features
from othello_coach.engine.eval import WEIGHTS
from othello_coach.engine.board import Board, make_move
from othello_coach.engine.movegen_fast import legal_moves_mask


TEMPLATES = [
    ("mobility", lambda d: f"Opens +{d['dM']} moves next and reduces their replies by {d['dOppM']}.") ,
    ("parity", lambda d: f"Preserves odd parity in the {d['region']} region."),
    ("x_square", lambda d: f"Avoids an X-square trap near {d['corner']}."),
    ("stability", lambda d: f"Increases stable discs by {d['dS']} this turn."),
    ("corner", lambda d: f"Gains corner control on {d['corner']} safely within 2 plies."),
]


def explain_move(board: Board, move: int) -> List[str]:
    feats_before = extract_features(board)
    b2, _ = make_move(board, move)
    feats_after = extract_features(b2)
    # Compute deltas
    d = {
        "dM": (feats_after["mobility_stm"] - feats_after["mobility_opp"]) - (feats_before["mobility_stm"] - feats_before["mobility_opp"]),
        "dOppM": feats_before["mobility_opp"] - feats_after["mobility_opp"],
        "dS": (feats_after["stability_stm"] - feats_before["stability_stm"]),
    }
    candidates: List[Tuple[float, str]] = []
    # Score reasons by magnitude times eval weights
    from othello_coach.engine.eval import WEIGHTS
    if d["dM"] > 0 or d["dOppM"] > 0:
        score = abs(d["dM"]) * WEIGHTS["mobility"]
        candidates.append((score, TEMPLATES[0][1]({"dM": d["dM"], "dOppM": d["dOppM"]})))
    if d["dS"] > 0:
        candidates.append((abs(d["dS"]) * WEIGHTS["stability"], TEMPLATES[3][1]({"dS": d["dS"]})))
    candidates.sort(key=lambda t: t[0], reverse=True)
    return [msg for _, msg in candidates[:2]]


def generate_rationale(board: Board, move: int) -> Dict[str, List[str]]:
    """Generate rationale for a move (API compatible version)"""
    explanations = explain_move(board, move)
    return {
        "explanations": explanations,
        "move": move,
        "position": f"{board.B:016x}_{board.W:016x}_{board.stm}"
    }