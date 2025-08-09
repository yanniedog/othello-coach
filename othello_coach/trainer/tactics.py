"""Tactics 2.0 puzzle generator"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from ..engine.board import Board
from ..engine.search import search_position
from ..engine.eval import evaluate_position


@dataclass
class TacticsPuzzle:
    """A tactics puzzle"""
    position_hash: int
    board: Board
    best_move: int
    best_score: float
    alternatives: List[Tuple[int, float]]  # (move, score) pairs
    hint_type: str
    hint_text: str
    difficulty: str  # 'easy', 'medium', 'hard'


class TacticsGenerator:
    """Generates tactics puzzles from positions"""
    
    HINT_TYPES = {
        'mobility': "Which move changes mobility most dramatically?",
        'parity': "Which move affects parity control?",
        'stability': "Which move increases your stable disc count?",
        'corner': "Which move helps secure corner access?",
        'tempo': "Which move maintains or gains tempo?",
        'frontier': "Which move minimizes your frontier exposure?"
    }
    
    def __init__(self, min_score_gap: float = 120.0, search_depth: int = 8):
        self.min_score_gap = min_score_gap  # Minimum gap between best and second-best
        self.search_depth = search_depth
    
    def generate_puzzle(self, board: Board) -> Optional[TacticsPuzzle]:
        """Generate a tactics puzzle from a position"""
        try:
            # Search the position to find best moves
            result = search_position(board, depth=self.search_depth, time_ms=2000)
            
            if not result or not result.pv:
                return None
            
            best_move = result.pv[0]
            best_score = result.score
            
            # Generate alternatives by searching other legal moves
            from ..engine.movegen_fast import generate_legal_mask
            legal_mask = generate_legal_mask(board.B, board.W, board.stm)
            
            alternatives = []
            for sq in range(64):
                if (legal_mask & (1 << sq)) and sq != best_move:
                    # Search this alternative
                    try:
                        test_board = self._make_move(board, sq)
                        alt_result = search_position(test_board, depth=self.search_depth-2, time_ms=1000)
                        if alt_result:
                            alternatives.append((sq, -alt_result.score))  # Negate for opponent's perspective
                    except:
                        continue
            
            if not alternatives:
                return None
            
            # Sort alternatives by score
            alternatives.sort(key=lambda x: x[1], reverse=True)
            second_best_score = alternatives[0][1] if alternatives else best_score - 200
            
            # Check if this is a good puzzle (significant gap)
            score_gap = best_score - second_best_score
            if score_gap < self.min_score_gap:
                return None
            
            # Determine hint type and difficulty
            hint_type, hint_text = self._analyze_position_for_hint(board, best_move)
            difficulty = self._determine_difficulty(score_gap, len(alternatives))
            
            return TacticsPuzzle(
                position_hash=board.hash,
                board=board,
                best_move=best_move,
                best_score=best_score,
                alternatives=alternatives[:5],  # Top 5 alternatives
                hint_type=hint_type,
                hint_text=hint_text,
                difficulty=difficulty
            )
            
        except Exception:
            return None
    
    def _make_move(self, board: Board, move: int) -> Board:
        """Make a move and return new board"""
        from ..engine.board import make_move
        new_board, _ = make_move(board, move)
        return new_board
    
    def _analyze_position_for_hint(self, board: Board, best_move: int) -> Tuple[str, str]:
        """Analyze position to determine appropriate hint"""
        # Get features before and after the move
        from ..insights.features import extract_features
        
        features_before = extract_features(board)
        board_after = self._make_move(board, best_move)
        features_after = extract_features(board_after)
        
        # Calculate deltas
        mobility_delta = features_after.get('mobility', 0) - features_before.get('mobility', 0)
        stability_delta = features_after.get('stability_proxy', 0) - features_before.get('stability_proxy', 0)
        
        # Determine dominant feature change
        if abs(mobility_delta) >= 3:
            return 'mobility', self.HINT_TYPES['mobility']
        elif stability_delta >= 2:
            return 'stability', self.HINT_TYPES['stability']
        elif self._is_corner_move(best_move):
            return 'corner', self.HINT_TYPES['corner']
        elif abs(mobility_delta) >= 1:
            return 'tempo', self.HINT_TYPES['tempo']
        else:
            return 'frontier', self.HINT_TYPES['frontier']
    
    def _is_corner_move(self, move: int) -> bool:
        """Check if move is corner-related"""
        corners = {0, 7, 56, 63}  # A1, H1, A8, H8
        return move in corners
    
    def _determine_difficulty(self, score_gap: float, num_alternatives: int) -> str:
        """Determine puzzle difficulty"""
        if score_gap >= 300 or num_alternatives <= 3:
            return 'easy'
        elif score_gap >= 200 or num_alternatives <= 6:
            return 'medium'
        else:
            return 'hard'
    
    def generate_puzzle_batch(self, positions: List[Board], max_puzzles: int = 50) -> List[TacticsPuzzle]:
        """Generate multiple puzzles from a list of positions"""
        puzzles = []
        
        for board in positions:
            if len(puzzles) >= max_puzzles:
                break
            
            puzzle = self.generate_puzzle(board)
            if puzzle:
                puzzles.append(puzzle)
        
        return puzzles
    
    def validate_solution(self, puzzle: TacticsPuzzle, user_move: int) -> Dict:
        """Validate user's solution attempt"""
        result = {
            'correct': user_move == puzzle.best_move,
            'user_move': user_move,
            'best_move': puzzle.best_move,
            'explanation': ""
        }
        
        if result['correct']:
            result['explanation'] = f"Correct! This move gains approximately {puzzle.best_score:.0f} centipawns."
        else:
            # Find user move in alternatives
            user_score = None
            for move, score in puzzle.alternatives:
                if move == user_move:
                    user_score = score
                    break
            
            if user_score is not None:
                score_diff = puzzle.best_score - user_score
                result['explanation'] = f"Not the best. Your move scores {user_score:.0f}cp, but {self._square_name(puzzle.best_move)} scores {puzzle.best_score:.0f}cp (+{score_diff:.0f}cp better)."
            else:
                result['explanation'] = f"Poor choice. The best move is {self._square_name(puzzle.best_move)} scoring {puzzle.best_score:.0f}cp."
        
        return result
    
    def _square_name(self, square: int) -> str:
        """Convert square index to algebraic notation"""
        file = chr(ord('a') + (square % 8))
        rank = str((square // 8) + 1)
        return file + rank
