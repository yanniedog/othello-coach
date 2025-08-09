from __future__ import annotations

from typing import Dict


def classify_mistake(delta: Dict[str, int], empties: int) -> str | None:
    if delta.get("mobility", 0) <= -3 and delta.get("opp_mob", 0) >= 2:
        return "Mobility leak"
    if delta.get("parity_flip", 0):
        return "Parity flip"
    if empties >= 24 and delta.get("frontier", 0) >= 3:
        return "Frontier bloat"
    if delta.get("x_poison", 0):
        return "X-square poison"
    if delta.get("score", 0) <= -60:
        return "Tempo waste"
    return None
