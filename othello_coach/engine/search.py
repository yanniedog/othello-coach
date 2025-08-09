from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
import math
import time
import random

from .bitboard import Position, legal_moves, popcount
from .eval import evaluate

TTEntry = Tuple[int, int, int, int]  # depth, score, flag, best_move
TT = Dict[int, TTEntry]

FLAG_EXACT, FLAG_ALPHA, FLAG_BETA = 0, 1, 2

@dataclass
class SearchConfig:
    max_depth: int = 6
    noise_temp: float = 0.0  # softmax temperature for move selection at root
    blunder_prob: float = 0.0
    node_limit: int = 0  # 0 = unlimited

@dataclass
class Analysis:
    best_move: Optional[int]
    score: int
    depth: int
    pv: List[int]
    nodes: int
    time_ms: int

class Searcher:
    def __init__(self):
        self.tt: TT = {}
        self.nodes = 0
        self.start_time = 0.0
        self.node_limit = 0

    def reset_stats(self):
        self.nodes = 0
        self.start_time = time.time()

    def pick_move_with_noise(self, scored_moves: List[Tuple[int,int]], temp: float, blunder_p: float) -> int:
        # scored_moves: list of (move, score)
        if blunder_p > 0 and random.random() < blunder_p:
            return random.choice([m for m,_ in scored_moves])
        if temp <= 1e-6:
            return max(scored_moves, key=lambda x: x[1])[0]
        # softmax
        mx = max(s for _, s in scored_moves)
        exps = [math.exp((s - mx)/max(1e-6,temp)) for _, s in scored_moves]
        Z = sum(exps)
        r = random.random() * Z
        acc = 0.0
        for (m,s), e in zip(scored_moves, exps):
            acc += e
            if r <= acc:
                return m
        return scored_moves[-1][0]

    def search(self, pos: Position, cfg: SearchConfig) -> Analysis:
        self.reset_stats()
        self.node_limit = cfg.node_limit
        best_move = None
        best_score = -10**9
        pv: List[int] = []
        alpha, beta = -10**9, 10**9
        for depth in range(1, cfg.max_depth+1):
            score, move, line = self._negamax(pos, depth, alpha, beta)
            if move is not None:
                best_move = move
                best_score = score
                pv = line
            if self.node_limit and self.nodes >= self.node_limit:
                break
        # Root noise / blunder handling: recompute root moves at small depth and sample
        if best_move is not None and (cfg.noise_temp > 0 or cfg.blunder_prob > 0):
            root_moves = self._score_root_moves(pos, min(3, cfg.max_depth))
            best_move = self.pick_move_with_noise(root_moves, cfg.noise_temp, cfg.blunder_prob)
        return Analysis(best_move, best_score, depth, pv, self.nodes, int(1000*(time.time()-self.start_time)))

    def _score_root_moves(self, pos: Position, depth: int) -> List[Tuple[int,int]]:
        lm = pos.legal_mask()
        moves = [i for i in range(64) if (lm >> i) & 1]
        scored = []
        for m in moves:
            child = pos.apply(m)
            s,_,_ = self._negamax(child, depth-1, -10**9, 10**9)
            scored.append((m, -s))
        if not scored:
            # pass move
            child = pos.pass_move()
            s,_,_ = self._negamax(child, depth-1, -10**9, 10**9)
            scored.append((64, -s))  # 64 denotes pass
        return scored

    def _negamax(self, pos: Position, depth: int, alpha: int, beta: int) -> Tuple[int, Optional[int], List[int]]:
        self.nodes += 1
        if self.node_limit and self.nodes >= self.node_limit:
            return evaluate(pos), None, []
        key = pos.hash64()
        if depth == 0 or pos.terminal():
            return evaluate(pos), None, []
        if key in self.tt:
            td, ts, tf, tm = self.tt[key]
            if td >= depth:
                if tf == FLAG_EXACT:
                    return ts, tm, [tm] if tm is not None and tm != 64 else []
                elif tf == FLAG_ALPHA and ts <= alpha:
                    return alpha, tm, [tm] if tm is not None and tm != 64 else []
                elif tf == FLAG_BETA and ts >= beta:
                    return beta, tm, [tm] if tm is not None and tm != 64 else []
        best_move = None
        best_score = -10**9
        pv: List[int] = []
        lm = pos.legal_mask()
        if lm == 0:
            # pass
            child = pos.pass_move()
            s,_,line = self._negamax(child, depth-1, -beta, -alpha)
            s = -s
            if s > best_score:
                best_score, best_move, pv = s, 64, []
            # store and return
            flag = FLAG_EXACT
            self.tt[key] = (depth, best_score, flag, best_move if best_move is not None else 64)
            return best_score, best_move, [best_move] + pv if best_move is not None else []
        moves = [i for i in range(64) if (lm >> i) & 1]
        # Simple move ordering: prefer corners, then eval guess
        def move_key(m):
            if m in (0,7,56,63):
                return 10_000
            return 0
        moves.sort(key=move_key, reverse=True)
        for m in moves:
            child = pos.apply(m)
            s, _, line = self._negamax(child, depth-1, -beta, -alpha)
            s = -s
            if s > best_score:
                best_score = s
                best_move = m
                pv = [m] + line
            if best_score > alpha:
                alpha = best_score
            if alpha >= beta:
                break
        flag = FLAG_EXACT
        if best_score <= alpha:
            flag = FLAG_ALPHA
        elif best_score >= beta:
            flag = FLAG_BETA
        self.tt[key] = (depth, best_score, flag, best_move if best_move is not None else 64)
        return best_score, best_move, pv


