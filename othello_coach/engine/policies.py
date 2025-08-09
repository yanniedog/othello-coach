from __future__ import annotations
from .search import SearchConfig

# Map approximate ELO bands to search config knobs.

def policy_for_elo(elo: int) -> SearchConfig:
    elo = max(200, min(2500, int(elo)))
    if elo <= 400:
        return SearchConfig(max_depth=2, noise_temp=1.0, blunder_prob=0.10)
    if elo <= 800:
        return SearchConfig(max_depth=4, noise_temp=0.6, blunder_prob=0.05)
    if elo <= 1400:
        return SearchConfig(max_depth=6, noise_temp=0.3, blunder_prob=0.02)
    if elo <= 2000:
        return SearchConfig(max_depth=9, noise_temp=0.1, blunder_prob=0.005)
    if elo <= 2300:
        return SearchConfig(max_depth=12, noise_temp=0.0, blunder_prob=0.0)
    return SearchConfig(max_depth=14, noise_temp=0.0, blunder_prob=0.0)


