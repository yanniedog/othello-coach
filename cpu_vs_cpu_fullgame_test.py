from __future__ import annotations

import os
import sys
import time

from othello_coach.engine.board import Board, start_board, make_move, compute_hash
from othello_coach.engine.movegen_fast import legal_moves_mask
from othello_coach.engine.search import Searcher, SearchLimits
from othello_coach.engine.solver import get_solver_threshold
from othello_coach.engine.strength import get_strength_profile
from othello_coach.tools.diag import log_event


def run_cpu_vs_cpu_game(black_profile_name: str = "elo_1400", white_profile_name: str = "elo_1400") -> tuple[int, int, int]:
    """Run a headless CPU vs CPU game to completion.

    Returns a tuple of (black_count, white_count, plies).
    Raises RuntimeError if the game fails to make progress within safety bounds.
    """

    # Ensure any exact solving is conservative to avoid stalls
    os.environ.setdefault("OTHELLO_COACH_RUST_EXACT", "0")

    board: Board = start_board()
    log_event(
        "test.cpu_game",
        "start",
        black_profile=black_profile_name,
        white_profile=white_profile_name,
    )
    searcher = Searcher()

    black_profile = get_strength_profile(black_profile_name)
    white_profile = get_strength_profile(white_profile_name)
    endgame_threshold = get_solver_threshold()

    max_plies_safety = 200
    no_progress_ticks = 0
    max_game_ms = 60_000
    max_move_ms = 2_000

    game_start = time.perf_counter()

    while True:
        # Check legal moves for current player
        mask = legal_moves_mask(board.B, board.W, board.stm)
        if mask == 0:
            # Check if opponent also has no moves → game over
            next_stm = 1 - board.stm
            opp_mask = legal_moves_mask(board.B, board.W, next_stm)
            if opp_mask == 0:
                log_event(
                    "test.cpu_game",
                    "game_over_no_moves",
                    ply=board.ply,
                    black_count=board.B.bit_count(),
                    white_count=board.W.bit_count(),
                )
                break
            # Apply pass
            board = Board(board.B, board.W, next_stm, board.ply + 1, compute_hash(board.B, board.W, next_stm))
            log_event("test.cpu_game", "pass", new_stm=board.stm, ply=board.ply)
            continue

        # Determine profile for side to move
        profile = black_profile if board.stm == 0 else white_profile

        limits = SearchLimits(
            max_depth=profile.depth,
            time_ms=min(profile.soft_time_ms, max_move_ms),
            node_cap=300_000,
            endgame_exact_empties=endgame_threshold,
        )
        empties = 64 - (board.B | board.W).bit_count()
        log_event(
            "test.cpu_game",
            "search_start",
            ply=board.ply,
            stm=board.stm,
            empties=empties,
            depth=profile.depth,
            time_ms=profile.soft_time_ms,
            node_cap=500_000,
            endgame_exact_empties=endgame_threshold,
        )

        # Reset nodes for this move
        try:
            searcher.nodes = 0
        except Exception:
            pass

        move_start = time.perf_counter()
        result = None
        try:
            result = searcher.search(board, limits)
        except Exception as e:
            log_event("test.cpu_game", "search_exception", error=str(e))
            result = None
        wall_ms = int((time.perf_counter() - move_start) * 1000)

        if (result is None) or (result.best_move is None) or (wall_ms > max_move_ms):
            # If for any reason no move is produced, pick the first legal move to ensure progress
            lsb = mask & -mask
            sq = lsb.bit_length() - 1
            log_event(
                "test.cpu_game",
                "fallback_move",
                ply=board.ply,
                stm=board.stm,
                chosen_sq=sq,
                wall_ms=wall_ms,
                reason=(
                    "timeout" if wall_ms > max_move_ms else (
                        "no_result" if result is None else "no_best_move"
                    )
                ),
            )
        else:
            sq = result.best_move

        before = (board.B, board.W, board.stm)
        board, _ = make_move(board, sq)
        after = (board.B, board.W, board.stm)
        post_empties = 64 - (board.B | board.W).bit_count()
        if result is not None:
            log_event(
                "test.cpu_game",
                "move",
                ply=board.ply,
                prev_stm=before[2],
                move_sq=sq,
                score_cp=result.score_cp,
                time_ms=result.time_ms,
                nodes=result.nodes,
                depth=result.depth,
                pv_len=len(result.pv),
                empties_before=empties,
                empties_after=post_empties,
                wall_ms=wall_ms,
            )
        else:
            log_event(
                "test.cpu_game",
                "move",
                ply=board.ply,
                prev_stm=before[2],
                move_sq=sq,
                score_cp=None,
                time_ms=None,
                nodes=None,
                depth=None,
                pv_len=None,
                empties_before=empties,
                empties_after=post_empties,
                wall_ms=wall_ms,
            )

        if result.time_ms <= 0:
            no_progress_ticks += 1
        else:
            no_progress_ticks = 0

        if no_progress_ticks >= 5:
            raise RuntimeError("Engine produced no progress for 5 consecutive moves")

        if board.ply > max_plies_safety:
            raise RuntimeError(f"Exceeded safety limit of {max_plies_safety} plies")

        # Global game timeout
        if int((time.perf_counter() - game_start) * 1000) > max_game_ms:
            raise RuntimeError(f"Exceeded global game timeout of {max_game_ms} ms")

    return board.B.bit_count(), board.W.bit_count(), board.ply


def main() -> int:
    try:
        t0 = time.perf_counter()
        b, w, plies = run_cpu_vs_cpu_game()
        dt = (time.perf_counter() - t0) * 1000
        log_event(
            "test.cpu_game",
            "end",
            black_count=b,
            white_count=w,
            plies=plies,
            time_ms=int(dt),
        )
        print(f"CPU vs CPU finished: Black={b} White={w} plies={plies} time_ms={int(dt)}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())


