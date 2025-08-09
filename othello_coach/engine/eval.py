from __future__ import annotations
from dataclasses import dataclass
from .bitboard import popcount, CORNER_MASK, EDGE_MASK, Position, legal_moves

# Phase-aware linear evaluation with common Othello features.

# Weights can be tuned later (self-play). These defaults are sane and conservative.
@dataclass
class EvalWeights:
    mobility: int = 80
    pot_mobility: int = 20
    corners: int = 800
    corner_adj_penalty: int = -120
    frontier: int = -20
    disc_diff: int = 2

DEFAULT_WEIGHTS = EvalWeights()


def potential_mobility(me: int, opp: int) -> int:
    # Number of empty squares adjacent to opponent discs
    empty = ~(me | opp) & 0xFFFFFFFFFFFFFFFF
    adj = 0
    # Adjacent using king moves
    adj |= ((opp << 8) | (opp >> 8)) & 0xFFFFFFFFFFFFFFFF
    left = (opp & 0xFEFEFEFEFEFEFEFE) << 1
    right = (opp & 0x7F7F7F7F7F7F7F7F) >> 1
    adj |= left | right
    adj |= ((left << 8) | (right << 8) | (left >> 8) | (right >> 8)) & 0xFFFFFFFFFFFFFFFF
    return popcount(adj & empty)


def frontier_discs(me: int, opp: int) -> int:
    empty = ~(me | opp) & 0xFFFFFFFFFFFFFFFF
    # A disc is frontier if adjacent to any empty
    adj_empty = 0
    adj_empty |= ((empty << 8) | (empty >> 8)) & 0xFFFFFFFFFFFFFFFF
    left = (empty & 0xFEFEFEFEFEFEFEFE) << 1
    right = (empty & 0x7F7F7F7F7F7F7F7F) >> 1
    adj_empty |= left | right
    adj_empty |= ((left << 8) | (right << 8) | (left >> 8) | (right >> 8)) & 0xFFFFFFFFFFFFFFFF
    return popcount(me & adj_empty)


def corner_score(me: int, opp: int) -> int:
    me_c = popcount(me & CORNER_MASK)
    opp_c = popcount(opp & CORNER_MASK)
    return (me_c - opp_c)


def corner_adjacent_penalty(me: int, opp: int) -> int:
    # Penalise occupying X/C squares early; approximate via adjacency to corners
    # X-squares: B2, G2, B7, G7 (indices 9, 14, 49, 54)
    xs = (1 << 9) | (1 << 14) | (1 << 49) | (1 << 54)
    cs = (
        (1 << 1) | (1 << 8) | (1 << 9) |
        (1 << 6) | (1 << 14) | (1 << 15) |
        (1 << 48) | (1 << 49) | (1 << 56) |
        (1 << 54) | (1 << 55) | (1 << 62)
    )
    me_bad = popcount(me & (xs | cs))
    opp_bad = popcount(opp & (xs | cs))
    return me_bad - opp_bad


def evaluate(pos: Position, weights: EvalWeights = DEFAULT_WEIGHTS) -> int:
    # Return centipawn-like score from side-to-move perspective (positive is good for stm)
    me, opp = pos.me_opp()
    mob_me = popcount(legal_moves(me, opp))
    mob_opp = popcount(legal_moves(opp, me))
    pot_mob = potential_mobility(me, opp) - potential_mobility(opp, me)
    corners_delta = corner_score(me, opp)
    corner_adj = corner_adjacent_penalty(me, opp)
    frontier = frontier_discs(me, opp) - frontier_discs(opp, me)
    disc = pos.score_disc_diff()
    if pos.stm == 1:
        disc = -disc
    # Phase blend: as board fills, rely more on disc diff
    empties = 64 - (popcount(pos.black | pos.white))
    phase = max(0, min(64, empties)) / 64.0
    score = 0
    score += weights.mobility * (mob_me - mob_opp)
    score += weights.pot_mobility * pot_mob
    score += weights.corners * corners_delta
    score += weights.corner_adj_penalty * corner_adj
    score += weights.frontier * frontier
    score += int((1 - phase) * weights.disc_diff * disc)
    return score


