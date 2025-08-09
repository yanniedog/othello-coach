"""Python wrapper for the Rust extension module.

This package exposes the functions compiled in ``rust_kernel._rust_kernel``
at the top-level ``rust_kernel`` namespace, matching the expectations of
the test suite and downstream imports.
"""

from __future__ import annotations

# Try to import the compiled extension first and expose its API. If unavailable,
# provide Python fallbacks that match the same function signatures.
try:  # Prefer the compiled extension submodule
    from ._rust_kernel import (  # type: ignore
        legal_mask,
        flip_mask,
        potential_mobility,
        stability_proxy,
        parity_regions,
        exact_solver,
    )
    AVAILABLE = True
    __all__ = [
        "legal_mask",
        "flip_mask",
        "potential_mobility",
        "stability_proxy",
        "parity_regions",
        "exact_solver",
        "AVAILABLE",
    ]
except Exception:  # Fall back to Python implementations
    AVAILABLE = False

    # Import Python equivalents to maintain the same public API
    from othello_coach.engine.movegen_fast import (
        generate_legal_mask as _py_legal_mask,
        generate_flip_mask as _py_generate_flip_mask,
    )
    from othello_coach.insights.features import extract_features as _extract_features
    from othello_coach.engine.solver import _python_exact_solver as _py_exact_solver
    from othello_coach.engine.board import Board as _Board

    def legal_mask(b: int, w: int, stm: int) -> int:
        return _py_legal_mask(b, w, stm)

    def flip_mask(b: int, w: int, stm: int, sq: int) -> int:
        # movegen_fast expects side-to-move bitboards for flip mask
        return _py_generate_flip_mask(b if stm == 0 else w, w if stm == 0 else b, sq)

    def potential_mobility(b: int, w: int, stm: int) -> int:
        feats = _extract_features(_Board(B=b, W=w, stm=stm, ply=0, hash=0))
        return int(feats.get('pot_mob_stm', 0))

    def stability_proxy(b: int, w: int) -> int:
        feats = _extract_features(_Board(B=b, W=w, stm=0, ply=0, hash=0))
        return int(feats.get('stability_stm', 0) - feats.get('stability_opp', 0))

    def parity_regions(b: int, w: int) -> list[tuple[int, int]]:
        empties = (~(b | w)) & 0xFFFFFFFFFFFFFFFF
        regions: list[tuple[int, int]] = []
        visited = 0
        rem = empties
        while rem:
            lsb = rem & -rem
            start = (lsb.bit_length() - 1)
            stack = [start]
            mask = 0
            while stack:
                s = stack.pop()
                if (visited >> s) & 1:
                    continue
                visited |= (1 << s)
                mask |= (1 << s)
                r, f = divmod(s, 8)
                for nb in (s-8 if r>0 else None, s+8 if r<7 else None, s-1 if f>0 else None, s+1 if f<7 else None):
                    if nb is None:
                        continue
                    if ((empties >> nb) & 1) and ((visited >> nb) & 1) == 0:
                        stack.append(nb)
            regions.append((mask, 2))
            rem &= ~mask
        return regions

    def exact_solver(b: int, w: int, stm: int, empties: int, tt_mb: int) -> int:
        board = _Board(B=b, W=w, stm=stm, ply=0, hash=0)
        return int(_py_exact_solver(board))

    __all__ = [
        "legal_mask",
        "flip_mask",
        "potential_mobility",
        "stability_proxy",
        "parity_regions",
        "exact_solver",
        "AVAILABLE",
    ]
