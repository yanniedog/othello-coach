from __future__ import annotations

import json
from importlib import resources
from typing import Dict


def load_theme(name: str) -> Dict:
    with resources.files("othello_coach.config.themes").joinpath(f"{name}.json").open("r", encoding="utf-8") as f:
        return json.load(f)
