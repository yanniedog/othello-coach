from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

EXACT, LOWER, UPPER = 0, 1, 2


@dataclass
class TTEntry:
    depth: int
    score: int
    flag: int
    best: int  # 0..63 or -1
    gen: int


class TranspositionTable:
    def __init__(self, capacity: int = 1_000_000) -> None:
        self.store: Dict[int, TTEntry] = {}
        self.gen: int = 0
        self.capacity = capacity
        self.stats = {"lookups": 0, "hits": 0, "stores": 0, "replacements": 0, "bounds_used": 0}

    def new_generation(self) -> None:
        self.gen = (self.gen + 1) & 0xFF

    def probe(self, key: int) -> TTEntry | None:
        self.stats["lookups"] += 1
        e = self.store.get(key)
        if e is not None:
            self.stats["hits"] += 1
        return e

    def save(self, key: int, depth: int, score: int, flag: int, best: int) -> None:
        self.stats["stores"] += 1
        e = self.store.get(key)
        entry = TTEntry(depth=depth, score=score, flag=flag, best=best, gen=self.gen)
        if e is None:
            self.store[key] = entry
            return
        replace = depth > e.depth or (self.gen - e.gen) % 256 >= 2
        if replace:
            self.stats["replacements"] += 1
            self.store[key] = entry

    def clear(self) -> None:
        self.store.clear()
