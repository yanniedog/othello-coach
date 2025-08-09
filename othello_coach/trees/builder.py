from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple

from othello_coach.engine.board import Board
from othello_coach.engine.movegen_fast import legal_moves_mask
from othello_coach.engine.board import make_move
from .presets import get_preset
from othello_coach.engine.eval import evaluate


@dataclass
class TreeNode:
    stm: int
    score: int
    attrs: dict


def build_tree(root: Board, preset: str, depth: int = 4, width: int = 8, time_ms: int = 2000) -> dict:
    start = time.perf_counter()
    nodes: Dict[int, TreeNode] = {root.hash: TreeNode(root.stm, 0, {})}
    edges: List[dict] = []
    frontier: List[Tuple[float, float, Board, int]] = []  # (priority, novelty, board, depth)
    scorer = get_preset(preset).scorer
    root_score = scorer(root)
    # Novelty v1.0 simple: 1.0 at root
    frontier.append((root_score + 0.01, 1.0, root, 0))
    while frontier and len(nodes) < 1_000 and (time.perf_counter() - start) * 1000 < time_ms:
        # best-first: pop max score
        frontier.sort(key=lambda t: (t[0], t[1]), reverse=True)
        cur_score, cur_novelty, cur, d = frontier.pop(0)
        mask = legal_moves_mask(cur.B, cur.W, cur.stm)
        m = mask
        w = 0
        while m and w < width and d < depth:
            lsb = m & -m
            sq = lsb.bit_length() - 1
            m ^= lsb
            w += 1
            b2, _ = make_move(cur, sq)
            if b2.hash not in nodes:
                score = scorer(b2)
                # Simple novelty: prefer positions not present yet (transposition-aware)
                novelty = 1.0 if b2.hash not in nodes else 0.3
                nodes[b2.hash] = TreeNode(b2.stm, int(score), {})
                # Priority tuple: primary score + small PV bonus + novelty
                pv_bonus = 0.001 * (depth - d)
                frontier.append((float(score) + pv_bonus + novelty, novelty, b2, d + 1))
            edges.append({"from": cur.hash, "to": b2.hash, "move": sq, "score": int(cur_score)})
    return {"root": root.hash, "nodes": {h: {"stm": n.stm, "score": n.score, "attrs": n.attrs} for h, n in nodes.items()}, "edges": edges}
