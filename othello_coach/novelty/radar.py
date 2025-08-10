"""Main novelty radar implementation"""

from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional
import math
from .shingles import SequenceShingles
from ..engine.board import Board


@dataclass
class NoveltyScore:
    """Novelty scoring result"""
    coverage: float  # 0.0-1.0, how much this line overlaps with known lines
    engine_interest: float  # 0.0-1.0, normalized eval gain vs siblings
    novelty_score: float  # combined score
    rank: Optional[int] = None  # ranking among candidates


class NoveltyRadar:
    """Detects and scores novel game lines"""
    
    def __init__(self, alpha: float = 0.7, beta: float = 0.3, k_plies: int = 6):
        self.alpha = alpha  # weight for coverage component
        self.beta = beta    # weight for engine interest component
        self.k_plies = k_plies  # depth for engine interest calculation
        
        self.shingles = SequenceShingles()
        self.known_lines: Dict[str, Set[Tuple[int, ...]]] = {}
        self.corpus_signatures: List[List[int]] = []
        
        # Load opening book and self-play corpus
        self._load_known_lines()
    
    def _load_known_lines(self):
        """Load known lines from openings and self-play corpus"""
        # Load opening book
        try:
            from ..openings.recogniser import OpeningRecogniser
            recogniser = OpeningRecogniser()
            
            opening_shingles = set()
            for line_name, moves in recogniser.book.items():
                if len(moves) >= 3:
                    # Convert to boards for shingle generation
                    boards = self._moves_to_boards(moves)
                    line_shingles = self.shingles.generate_shingles(moves, boards)
                    opening_shingles.update(line_shingles)
            
            self.known_lines['openings'] = opening_shingles
        except Exception:
            self.known_lines['openings'] = set()
        
        # Load self-play corpus (would be populated from database)
        self.known_lines['selfplay'] = set()
    
    def _moves_to_boards(self, moves: List[int]) -> List[Board]:
        """Convert move sequence to board sequence"""
        from ..engine.board import Board, make_move
        
        boards = []
        current_board = Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=0)
        boards.append(current_board)
        
        for move in moves:
            try:
                current_board, _ = make_move(current_board, move)
                boards.append(current_board)
            except:
                break  # Invalid move sequence
        
        return boards
    
    def add_selfplay_line(self, moves: List[int], boards: List[Board]):
        """Add a self-play line to the corpus"""
        if len(moves) >= 3:
            line_shingles = self.shingles.generate_shingles(moves, boards)
            self.known_lines['selfplay'].update(line_shingles)
    
    def calculate_coverage(self, moves: List[int], boards: List[Board]) -> float:
        """Calculate coverage (similarity to known lines)"""
        if len(moves) < 3:
            return 0.0
        
        line_shingles = self.shingles.generate_shingles(moves, boards)
        
        max_similarity = 0.0
        for corpus_name, corpus_shingles in self.known_lines.items():
            if corpus_shingles:
                similarity = self.shingles.jaccard_similarity(line_shingles, corpus_shingles)
                max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def calculate_engine_interest(self, moves: List[int], boards: List[Board], 
                                 scores: List[float]) -> float:
        """Calculate engine interest based on eval gains"""
        if len(moves) < 2 or len(scores) != len(moves):
            return 0.0
        
        # Calculate eval gains over first k plies
        eval_gains = []
        for i in range(1, min(len(scores), self.k_plies + 1)):
            if i < len(scores):
                # Eval gain relative to previous position
                gain = abs(scores[i] - scores[i-1])
                eval_gains.append(gain)
        
        if not eval_gains:
            return 0.0
        
        # Normalize by average gain (simple heuristic)
        avg_gain = sum(eval_gains) / len(eval_gains)
        normalized_interest = min(1.0, avg_gain / 100.0)  # 100cp = full interest
        
        return normalized_interest
    
    def score_novelty(self, moves: List[int], boards: List[Board], 
                     scores: List[float]) -> NoveltyScore:
        """Calculate complete novelty score"""
        coverage = self.calculate_coverage(moves, boards)
        engine_interest = self.calculate_engine_interest(moves, boards, scores)
        
        # Combined novelty score
        novelty_score = self.alpha * (1.0 - coverage) + self.beta * engine_interest
        
        return NoveltyScore(
            coverage=coverage,
            engine_interest=engine_interest,
            novelty_score=novelty_score
        )
    
    def rank_candidates(self, candidates: List[Tuple[List[int], List[Board], List[float]]]) -> List[NoveltyScore]:
        """Rank multiple candidate lines by novelty"""
        scores = []
        for moves, boards, evals in candidates:
            score = self.score_novelty(moves, boards, evals)
            scores.append(score)
        
        # Sort by novelty score (descending)
        sorted_indices = sorted(range(len(scores)), 
                              key=lambda i: scores[i].novelty_score, 
                              reverse=True)
        
        # Assign ranks
        ranked_scores = []
        for rank, idx in enumerate(sorted_indices):
            score = scores[idx]
            score.rank = rank + 1
            ranked_scores.append(score)
        
        return ranked_scores
