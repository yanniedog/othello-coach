from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional

from .board import Board, make_move, compute_hash
from .movegen_fast import legal_moves_mask
from .eval import evaluate
from .solver import solve_exact
from .tt import TranspositionTable, EXACT, LOWER, UPPER


@dataclass
class SearchLimits:
    max_depth: int = 6
    time_ms: int = 1000
    node_cap: int = 5_000_000
    endgame_exact_empties: int = 12


@dataclass
class SearchResult:
    best_move: int | None
    score_cp: int
    depth: int
    nodes: int
    time_ms: int
    pv: List[int]


class Searcher:
    def __init__(self) -> None:
        self.tt = TranspositionTable()
        self.nodes = 0
        # Killer moves: two killers per ply index
        self.killers: List[List[int]] = [[-1, -1] for _ in range(128)]
        # History heuristic: move (0..63) → score
        self.history: List[int] = [0 for _ in range(64)]

    def search(self, board: Board, limits: SearchLimits) -> SearchResult:
        start = time.perf_counter()
        best_move = None
        best_score = -10_000
        pv: List[int] = []
        self.tt.new_generation()
        aspiration = 50
        for depth in range(1, limits.max_depth + 1):
            alpha = best_score - aspiration
            beta = best_score + aspiration
            score, line = self._negamax(board, depth, alpha, beta, start, limits, ply=0)
            # Aspiration ladder per spec: widen to ±100 then ±200
            if score <= alpha or score >= beta:
                alpha = best_score - 100
                beta = best_score + 100
                score, line = self._negamax(board, depth, alpha, beta, start, limits, ply=0)
                if score <= alpha or score >= beta:
                    alpha = best_score - 200
                    beta = best_score + 200
                    score, line = self._negamax(board, depth, alpha, beta, start, limits, ply=0)
            best_score = score
            pv = line
            best_move = line[0] if line else None
            self.tt.new_generation()
            if (time.perf_counter() - start) * 1000 > limits.time_ms:
                break
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return SearchResult(best_move, best_score, len(pv), self.nodes, elapsed_ms, pv)

    def _negamax(self, board: Board, depth: int, alpha: int, beta: int, start, limits: SearchLimits, ply: int) -> Tuple[int, List[int]]:
        if self.nodes >= limits.node_cap or (time.perf_counter() - start) * 1000 > limits.time_ms:
            return evaluate(board), []
        empties = 64 - (board.B | board.W).bit_count()
        if empties <= limits.endgame_exact_empties:
            return solve_exact(board), []
        if depth == 0:
            return evaluate(board), []

        self.nodes += 1
        entry = self.tt.probe(board.hash)
        if entry and entry.depth >= depth:
            if entry.flag == EXACT:
                return entry.score, []
            if entry.flag == LOWER:
                alpha = max(alpha, entry.score)
            elif entry.flag == UPPER:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score, []

        mask = legal_moves_mask(board.B, board.W, board.stm)
        if mask == 0:
            # Toggle stm and update hash accordingly
            new_stm = 1 - board.stm
            b_pass = Board(board.B, board.W, new_stm, board.ply + 1, compute_hash(board.B, board.W, new_stm))
            score, line = self._negamax(b_pass, depth - 1, -beta, -alpha, start, limits, ply+1)
            return -score, []

        # Generate moves list
        moves: List[int] = []
        m = mask
        while m:
            lsb = m & -m
            moves.append(lsb.bit_length() - 1)
            m ^= lsb
        corners = {0, 7, 56, 63}
        tt_move: Optional[int] = None
        if entry and entry.best >= 0:
            tt_move = entry.best

        # Order moves using priority: TT → killers → corners → history desc
        def move_key(sq: int) -> tuple:
            is_tt = 0 if (tt_move is not None and sq == tt_move) else 1
            is_killer = 0 if (sq in self.killers[ply]) else 1
            is_corner = 0 if (sq in corners) else 1
            hist = -self.history[sq]
            return (is_tt, is_killer, is_corner, hist)

        moves.sort(key=move_key)

        best_score = -10_000
        best_line: List[int] = []
        current_mobility = mask.bit_count()
        for i, sq in enumerate(moves):
            b2, _ = make_move(board, sq)
            # LMR per spec: apply when conditions met
            new_depth = depth - 1
            is_tt = (tt_move is not None and sq == tt_move)
            is_killer = (sq in self.killers[ply])
            is_corner = (sq in corners)
            reduced = False
            if depth >= 3 and i >= 1 and (not is_tt) and (not is_killer) and (not is_corner):
                next_mobility = legal_moves_mask(b2.B, b2.W, b2.stm).bit_count()
                if next_mobility >= min(3, current_mobility):
                    r = max(1, int((1 + i).bit_length() - 1))  # floor(log2(1+i))
                    r = min(r, depth - 2)
                    if r > 0:
                        new_depth = max(1, depth - 1 - r)
                        reduced = True

            score, line = self._negamax(b2, new_depth, -beta, -alpha, start, limits, ply+1)
            score = -score
            # Verification search for reduced moves that raise alpha
            if reduced and score > alpha:
                score, line = self._negamax(b2, depth - 1, -beta, -alpha, start, limits, ply+1)
                score = -score
            if score > best_score:
                best_score = score
                best_line = [sq] + line
            if score > alpha:
                alpha = score
            if alpha >= beta:
                # Beta cutoff: update killers and history
                if self.killers[ply][0] != sq:
                    self.killers[ply][1] = self.killers[ply][0]
                    self.killers[ply][0] = sq
                self.history[sq] = min(self.history[sq] + depth * depth, 10_000)
                break
        # Store in TT with appropriate bound
        flag = EXACT
        if best_score <= alpha:
            flag = UPPER
        elif best_score >= beta:
            flag = LOWER
        self.tt.save(board.hash, depth, best_score, flag, best_line[0] if best_line else -1)
        return best_score, best_line
