from __future__ import annotations
from typing import List, Tuple, Optional

# Minimal embedded book with a few common names; extendable via JSON later.
# Moves are given as 0..63 indices. We use algebra like "D3" externally.

OPENINGS = [
    ("Parallel",        [19, 26]),
    ("Perpendicular",   [20, 29]),
    ("Diagonal",        [19, 29]),
    ("Tiger",           [18, 29, 45]),
    ("Cow",             [18, 29, 44]),
]

FILES = "ABCDEFGH"


def sq_to_alg(sq: int) -> str:
    r, c = divmod(sq, 8)
    return f"{FILES[c]}{r+1}"


def name_for_prefix(moves: List[int]) -> Optional[Tuple[str,str]]:
    # Return (name, variation) if prefix matches any book line
    best = None
    best_len = 0
    for name, line in OPENINGS:
        L = min(len(moves), len(line))
        if moves[:L] == line[:L] and L > best_len:
            best = (name, "Main" if len(moves) == len(line) else "…")
            best_len = L
    return best


