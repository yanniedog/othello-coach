from __future__ import annotations
import argparse
from multiprocessing import Pool
from typing import List, Tuple

from ..engine.bitboard import Position
from ..engine.search import Searcher
from ..engine.policies import policy_for_elo
from ..db.store import record_game, upsert_position, upsert_analysis, record_move


def _play_one_entry(args_tuple):
    return play_one(*args_tuple)


def play_one(seed:int, elo:int=1600, depth:int|None=None) -> Tuple[int,int,int,str]:
    import random
    random.seed(seed)
    pos = Position.initial()
    hist: List[int] = []
    eng = Searcher()
    cfg = policy_for_elo(elo)
    if depth is not None:
        cfg.max_depth = depth
    start_hash = pos.hash64()
    while not pos.terminal():
        a = eng.search(pos, cfg)
        upsert_position(pos.hash64(), pos.black, pos.white, pos.stm)
        if a.best_move is None:
            pos = pos.pass_move()
            continue
        move = a.best_move
        upsert_analysis(pos.hash64(), a.depth, a.score, 0, move, a.nodes, a.time_ms)
        to = pos.apply(move)
        record_move(pos.hash64(), move, to.hash64(), score=a.score/100.0)
        pos = to
        hist.append(move)
        if len(hist) > 200:
            break
    diff = pos.score_disc_diff()
    result = 1 if diff>0 else (-1 if diff<0 else 0)  # from Black POV
    pgn = ",".join(map(str, hist))
    gid = record_game(start_hash, result, len(hist), {"elo":elo}, pgn)
    return gid, result, len(hist), pgn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--elo", type=int, default=1600)
    ap.add_argument("--depth", type=int, default=None)
    args = ap.parse_args()
    seeds = list(range(args.games))
    if args.workers <= 1:
        for s in seeds:
            gid, res, L, pgn = play_one(s, args.elo, args.depth)
            print(f"game {gid}: result={res} len={L}")
        return
    with Pool(processes=args.workers) as pool:
        for gid, res, L, pgn in pool.imap_unordered(_play_one_entry, [(s, args.elo, args.depth) for s in seeds]):
            print(f"game {gid}: result={res} len={L}")

if __name__ == "__main__":
    main()


