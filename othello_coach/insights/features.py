from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Set, Tuple

from othello_coach.engine.board import Board
from othello_coach.engine.movegen_fast import legal_moves_mask
from othello_coach.engine.movegen_fast import legal_moves_mask


@lru_cache(maxsize=100000)
def extract_features_cached(hash_key: int, B: int, W: int, stm: int) -> Dict[str, int]:
    opp_stm = 1 - stm
    mask_stm = legal_moves_mask(B, W, stm)
    mask_opp = legal_moves_mask(B, W, opp_stm)
    empties = ~(B | W) & 0xFFFFFFFFFFFFFFFF
    # Squares adjacent to empties (8-neighborhood)
    adj_mask = (
        ((empties << 1) | (empties >> 1) | (empties << 8) | (empties >> 8) |
         (empties << 9) | (empties >> 9) | (empties << 7) | (empties >> 7))
        & 0xFFFFFFFFFFFFFFFF
    )
    opp = W if stm == 0 else B
    pot_mob_stm = (opp & adj_mask).bit_count()
    own = B if stm == 0 else W
    pot_mob_opp = (own & adj_mask).bit_count()
    corners = [0, 7, 56, 63]
    corners_stm = sum(1 for c in corners if ((own >> c) & 1))
    corners_opp = sum(1 for c in corners if ((opp >> c) & 1))
    # Frontier discs are discs adjacent to any empty square
    frontier_stm = (own & adj_mask).bit_count()
    frontier_opp = (opp & adj_mask).bit_count()
    # X/C risk: penalise X-square occupancy with higher risk when adjacent corner empty
    x_squares = [9, 14, 49, 54]
    c_squares = [1, 6, 57, 62]
    corners_idx = [0, 7, 56, 63]
    x_c_risk = 0
    for xi, ci, co in zip(x_squares, c_squares, corners_idx):
        if (own >> xi) & 1:
            risk = 1
            corner_empty = (((B | W) >> co) & 1) == 0
            c_own = ((own >> ci) & 1) == 1
            c_opp = ((opp >> ci) & 1) == 1
            if corner_empty and c_opp:
                risk += 2
            elif corner_empty and not c_own:
                risk += 1
            x_c_risk += risk

    # Parity regions: connected components of empties (4-neighbour)
    def neighbours4(sq: int) -> List[int]:
        r, f = divmod(sq, 8)
        res = []
        if r > 0:
            res.append(sq - 8)
        if r < 7:
            res.append(sq + 8)
        if f > 0:
            res.append(sq - 1)
        if f < 7:
            res.append(sq + 1)
        return res

    empties_list: List[int] = []
    tmp_e = empties
    while tmp_e:
        lsb = tmp_e & -tmp_e
        empties_list.append(lsb.bit_length() - 1)
        tmp_e ^= lsb
    seen: Set[int] = set()
    odd_regions = 0
    stm_access = 0
    opp_access = 0
    for s in empties_list:
        if s in seen:
            continue
        # BFS to collect region
        q = [s]
        seen.add(s)
        region: List[int] = []
        while q:
            cur = q.pop()
            region.append(cur)
            for nb in neighbours4(cur):
                if nb not in seen and ((empties >> nb) & 1):
                    seen.add(nb)
                    q.append(nb)
        if len(region) % 2 == 1:
            odd_regions += 1
            # Check access: any legal move landing in region for each side
            # Approximate by checking moves for each side and intersecting
            ms = legal_moves_mask(B, W, stm)
            mo = legal_moves_mask(B, W, opp_stm)
            reg_mask = 0
            for sq in region:
                reg_mask |= (1 << sq)
            if ms & reg_mask:
                stm_access += 1
            if mo & reg_mask:
                opp_access += 1
    parity_pressure = max(0, stm_access - opp_access)

    # Stability proxy: anchored discs flood from corners along rays until broken
    def stable_count(mask_color: int, mask_other: int) -> int:
        stable = 0
        for corner in corners_idx:
            if ((mask_color >> corner) & 1) == 0:
                continue
            # extend along two edges from the corner
            directions = []
            if corner == 0:
                directions = [1, 8]
            elif corner == 7:
                directions = [-1, 8]
            elif corner == 56:
                directions = [1, -8]
            elif corner == 63:
                directions = [-1, -8]
            for d in directions:
                cur = corner
                while True:
                    nr = cur + d
                    if nr < 0 or nr >= 64:
                        break
                    # Stop at edge crossings
                    if d == 1 and (nr % 8 == 0):
                        break
                    if d == -1 and (nr % 8 == 7):
                        break
                    if ((mask_color >> nr) & 1) == 0:
                        break
                    stable += 1
                    cur = nr
        return stable

    stability_stm = stable_count(own, opp)
    stability_opp = stable_count(opp, own)
    return {
        "mobility_stm": mask_stm.bit_count(),
        "mobility_opp": mask_opp.bit_count(),
        "pot_mob_stm": pot_mob_stm,
        "pot_mob_opp": pot_mob_opp,
        "corners_stm": corners_stm,
        "corners_opp": corners_opp,
        "frontier_stm": frontier_stm,
        "frontier_opp": frontier_opp,
        "x_c_risk": x_c_risk,
        "parity_pressure": parity_pressure,
        "stability_stm": stability_stm,
        "stability_opp": stability_opp,
        "disc_stm": own.bit_count(),
        "disc_opp": opp.bit_count(),
    }


def extract_features(board: Board) -> Dict[str, int]:
    return extract_features_cached(board.hash, board.B, board.W, board.stm)
