from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StrengthProfile:
    depth: int
    soft_time_ms: int
    noise_temp: float
    blunder_prob: float
    top_k: int


PROFILES = {
    "elo_400": StrengthProfile(2, 150, 1.0, 0.10, 3),
    "elo_800": StrengthProfile(4, 300, 0.6, 0.05, 3),
    # Map elo_1600 between 1400 and 2000 per spec default
    "elo_1600": StrengthProfile(6, 500, 0.3, 0.02, 2),
    "elo_1400": StrengthProfile(6, 500, 0.3, 0.02, 2),
    "elo_2000": StrengthProfile(9, 1200, 0.1, 0.005, 2),
    "elo_2300": StrengthProfile(12, 2500, 0.0, 0.0, 1),
    "max": StrengthProfile(14, 4000, 0.0, 0.0, 1),
}
