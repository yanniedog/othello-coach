"""Parity and endgame drill implementations"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from ..engine.board import Board
from ..engine.solver import solve_exact
from ..insights.features import extract_features


@dataclass
class ParityDrill:
    """Parity training drill"""
    position_hash: int
    board: Board
    target_region: int  # Region mask that should maintain odd parity
    correct_moves: List[int]
    explanation: str


@dataclass
class EndgameDrill:
    """Endgame training drill"""
    position_hash: int
    board: Board
    empties: int
    best_move: int
    exact_score: float
    time_limit: int = 10  # seconds


class ParityDrills:
    """Generate and validate parity drills"""
    
    def __init__(self):
        pass
    
    def generate_drill(self, board: Board) -> Optional[ParityDrill]:
        """Generate a parity drill from a position"""
        try:
            features = extract_features(board)
            parity_regions = features.get('parity_regions', [])
            
            # Find regions with odd parity that are significant
            target_regions = []
            for region_mask, controller, size in parity_regions:
                if size >= 5 and size % 2 == 1:  # Odd-sized regions
                    target_regions.append((region_mask, controller, size))
            
            if not target_regions:
                return None
            
            # Pick the largest odd region
            target_region_mask, controller, size = max(target_regions, key=lambda x: x[2])
            
            # Find moves that preserve parity in this region
            from ..engine.movegen_fast import generate_legal_mask
            legal_mask = generate_legal_mask(board.B, board.W, board.stm)
            
            correct_moves = []
            for sq in range(64):
                if (legal_mask & (1 << sq)):
                    # Test if this move preserves parity
                    if self._preserves_parity(board, sq, target_region_mask):
                        correct_moves.append(sq)
            
            if not correct_moves:
                return None
            
            explanation = f"Preserve odd parity in the {size}-square region. " \
                         f"Choose a move that keeps this region odd-sized."
            
            return ParityDrill(
                position_hash=board.hash,
                board=board,
                target_region=target_region_mask,
                correct_moves=correct_moves,
                explanation=explanation
            )
            
        except Exception:
            return None
    
    def _preserves_parity(self, board: Board, move: int, region_mask: int) -> bool:
        """Check if a move preserves odd parity in a region"""
        move_bit = 1 << move
        
        # If move is in the region, it reduces size by 1 (odd->even, bad)
        if region_mask & move_bit:
            return False
        
        # If move is adjacent to region, analyze effect
        # This is a simplified check - full implementation would simulate
        return True  # Simplified for now
    
    def validate_solution(self, drill: ParityDrill, user_move: int) -> Dict:
        """Validate user's parity drill solution"""
        correct = user_move in drill.correct_moves
        
        result = {
            'correct': correct,
            'user_move': user_move,
            'correct_moves': drill.correct_moves,
            'explanation': drill.explanation
        }
        
        if correct:
            result['feedback'] = "Correct! This move preserves the odd parity."
        else:
            result['feedback'] = f"Incorrect. Moves that preserve parity: {[self._square_name(m) for m in drill.correct_moves[:3]]}"
        
        return result
    
    def _square_name(self, square: int) -> str:
        """Convert square index to algebraic notation"""
        file = chr(ord('a') + (square % 8))
        rank = str((square // 8) + 1)
        return file + rank


class EndgameDrills:
    """Generate and validate endgame drills"""
    
    def __init__(self, max_empties: int = 16):
        self.max_empties = max_empties
    
    def generate_drill(self, board: Board) -> Optional[EndgameDrill]:
        """Generate an endgame drill from a position"""
        try:
            empties = 64 - bin(board.B | board.W).count('1')
            
            if empties > self.max_empties or empties < 4:
                return None
            
            # Use exact solver to find the best move
            best_score, best_move = self._solve_position(board)
            
            if best_move is None:
                return None
            
            # Verify this is a position where the best move is unique/critical
            if not self._is_critical_position(board, best_move, best_score):
                return None
            
            return EndgameDrill(
                position_hash=board.hash,
                board=board,
                empties=empties,
                best_move=best_move,
                exact_score=best_score,
                time_limit=10
            )
            
        except Exception:
            return None
    
    def _solve_position(self, board: Board) -> Tuple[Optional[float], Optional[int]]:
        """Solve position exactly"""
        try:
            empties = 64 - bin(board.B | board.W).count('1')
            
            # Use rust solver if available, otherwise Python
            try:
                import rust_kernel
                score = rust_kernel.exact_solver(board.B, board.W, board.stm, empties, 64)
                
                # Find the move that leads to this score
                best_move = self._find_best_move(board, score)
                return score / 100.0, best_move  # Convert from centipawns
                
            except ImportError:
                # Fallback to Python solver
                result = solve_exact(board, empties)
                if result:
                    return result.score, result.best_move
                
        except Exception:
            pass
        
        return None, None
    
    def _find_best_move(self, board: Board, target_score: float) -> Optional[int]:
        """Find the move that achieves the target score"""
        from ..engine.movegen_fast import generate_legal_mask
        legal_mask = generate_legal_mask(board.B, board.W, board.stm)
        
        for sq in range(64):
            if (legal_mask & (1 << sq)):
                try:
                    # Make move and solve resulting position
                    test_board = self._make_move(board, sq)
                    empties = 64 - bin(test_board.B | test_board.W).count('1')
                    
                    try:
                        import rust_kernel
                        score = rust_kernel.exact_solver(test_board.B, test_board.W, 
                                                       test_board.stm, empties, 64)
                        if abs(score + target_score) < 1:  # Account for negamax
                            return sq
                    except ImportError:
                        pass
                except:
                    continue
        
        return None
    
    def _make_move(self, board: Board, move: int) -> Board:
        """Make a move and return new board"""
        from ..engine.board import make_move
        return make_move(board, move)
    
    def _is_critical_position(self, board: Board, best_move: int, best_score: float) -> bool:
        """Check if this is a position where precision matters"""
        # Position is critical if:
        # 1. The score difference between moves is significant
        # 2. There are multiple reasonable-looking moves
        # For now, simplified check
        return abs(best_score) >= 2  # At least 2-disc difference
    
    def validate_solution(self, drill: EndgameDrill, user_move: int, 
                         time_taken: float) -> Dict:
        """Validate user's endgame drill solution"""
        correct = user_move == drill.best_move
        time_bonus = max(0, drill.time_limit - time_taken) / drill.time_limit
        
        result = {
            'correct': correct,
            'user_move': user_move,
            'best_move': drill.best_move,
            'time_taken': time_taken,
            'time_bonus': time_bonus,
            'exact_score': drill.exact_score
        }
        
        if correct:
            result['feedback'] = f"Perfect! The exact score is {drill.exact_score:+.1f} discs. Time bonus: {time_bonus:.1%}"
        else:
            result['feedback'] = f"Incorrect. The best move is {self._square_name(drill.best_move)} " \
                               f"leading to {drill.exact_score:+.1f} discs exactly."
        
        return result
    
    def _square_name(self, square: int) -> str:
        """Convert square index to algebraic notation"""
        file = chr(ord('a') + (square % 8))
        rank = str((square // 8) + 1)
        return file + rank
