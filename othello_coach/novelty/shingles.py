"""Sequence shingles and transposition normalization for novelty detection"""

from typing import Set, List, Tuple, Dict
import hashlib
from ..engine.board import Board


class TranspositionNormalizer:
    """Normalizes move sequences to canonical form for transposition awareness"""
    
    def __init__(self):
        self.canonical_cache: Dict[int, int] = {}
    
    def normalize_sequence(self, moves: List[int], boards: List[Board]) -> List[int]:
        """Convert sequence to transposition-canonical form"""
        canonical_moves = []
        
        for i, (move, board) in enumerate(zip(moves, boards)):
            # Get canonical hash for this position
            canonical_hash = self._get_canonical_hash(board)
            canonical_moves.append(canonical_hash)
        
        return canonical_moves
    
    def _get_canonical_hash(self, board: Board) -> int:
        """Get canonical hash considering symmetries"""
        # For now, use regular hash - could add symmetry detection later
        if board.hash in self.canonical_cache:
            return self.canonical_cache[board.hash]
        
        # Could implement 8-fold symmetry detection here
        canonical = board.hash
        self.canonical_cache[board.hash] = canonical
        return canonical


class SequenceShingles:
    """Generate n-gram shingles from move sequences"""
    
    def __init__(self, n_values: List[int] = None):
        self.n_values = n_values or [3, 4, 5]
        self.normalizer = TranspositionNormalizer()
    
    def generate_shingles(self, moves: List[int], boards: List[Board]) -> Set[Tuple[int, ...]]:
        """Generate all n-gram shingles for a sequence"""
        if len(moves) != len(boards):
            raise ValueError("Moves and boards must have same length")
        
        # Normalize sequence for transpositions
        canonical_moves = self.normalizer.normalize_sequence(moves, boards)
        
        shingles = set()
        for n in self.n_values:
            for i in range(len(canonical_moves) - n + 1):
                shingle = tuple(canonical_moves[i:i+n])
                shingles.add(shingle)
        
        return shingles
    
    def jaccard_similarity(self, shingles_a: Set[Tuple[int, ...]], 
                          shingles_b: Set[Tuple[int, ...]]) -> float:
        """Calculate Jaccard similarity between two shingle sets"""
        if not shingles_a and not shingles_b:
            return 1.0
        if not shingles_a or not shingles_b:
            return 0.0
        
        intersection = len(shingles_a & shingles_b)
        union = len(shingles_a | shingles_b)
        
        return intersection / union if union > 0 else 0.0
    
    def min_hash_signature(self, shingles: Set[Tuple[int, ...]], 
                          num_hashes: int = 128) -> List[int]:
        """Generate MinHash signature for approximate similarity"""
        if not shingles:
            return [0] * num_hashes
        
        signature = []
        for i in range(num_hashes):
            min_hash = float('inf')
            for shingle in shingles:
                # Create hash with salt
                hash_input = f"{i}:{shingle}".encode('utf-8')
                hash_val = int(hashlib.md5(hash_input).hexdigest()[:8], 16)
                min_hash = min(min_hash, hash_val)
            signature.append(int(min_hash))
        
        return signature
    
    def estimate_similarity(self, sig_a: List[int], sig_b: List[int]) -> float:
        """Estimate Jaccard similarity from MinHash signatures"""
        if len(sig_a) != len(sig_b):
            raise ValueError("Signatures must have same length")
        
        matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
        return matches / len(sig_a)
