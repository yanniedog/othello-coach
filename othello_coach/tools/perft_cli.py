from __future__ import annotations

import argparse
from time import perf_counter
from othello_coach.engine.board import start_board, Board
from othello_coach.engine.perft import perft, play_moves


def main() -> None:
    p = argparse.ArgumentParser(prog="othello-perft")
    p.add_argument("--depth", type=int, required=True)
    p.add_argument("--position", type=str, default=None, help="sequence like e6d6... or FEN (todo)")
    args = p.parse_args()

    b = start_board()
    if args.position:
        # simple moves list support
        moves = [args.position[i : i + 2] for i in range(0, len(args.position), 2)]
        b = play_moves(b, moves)
    t0 = perf_counter()
    n = perft(b, args.depth)
    dt = perf_counter() - t0
    print(f"perft(d={args.depth})={n} in {dt:.3f}s")
