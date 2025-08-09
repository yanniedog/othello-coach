from __future__ import annotations

import json
from importlib import resources
from typing import List, Tuple


def load_book() -> dict:
    with resources.files("othello_coach.openings").joinpath("book.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def recognise_prefix(moves: List[int]) -> Tuple[int, List[int]]:
    book = load_book()
    best_len = 0
    best_line: List[int] = []
    for line in book.get("lines", []):
        l = 0
        while l < len(moves) and l < len(line) and moves[l] == line[l]:
            l += 1
        if l > best_len:
            best_len = l
            best_line = line
    return best_len, best_line
