from __future__ import annotations

import argparse
import json

from othello_coach.engine.board import start_board
from othello_coach.trees.builder import build_tree


def main() -> None:
    p = argparse.ArgumentParser(prog="othello-tree")
    p.add_argument("--preset", required=True, choices=["score_side", "min_opp_mob", "early_corner"])
    p.add_argument("--depth", type=int, default=4)
    p.add_argument("--width", type=int, default=8)
    p.add_argument("--out", required=True)
    args = p.parse_args()

    root = start_board()
    tree = build_tree(root, args.preset, depth=args.depth, width=args.width)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(tree, f)
    print(f"wrote {args.out}")
