from othello_coach.engine.board import start_board
from othello_coach.engine.search import Searcher, SearchLimits


def test_search_basic_runs_and_returns_pv():
    b = start_board()
    s = Searcher()
    res = s.search(b, SearchLimits(max_depth=3, time_ms=500))
    assert res.best_move is not None
    assert isinstance(res.score_cp, int)
    assert res.depth >= 1
    assert res.nodes > 0
    assert len(res.pv) >= 1

