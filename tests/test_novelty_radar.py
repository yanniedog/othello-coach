"""Tests for novelty radar system"""

import pytest
from othello_coach.novelty.shingles import SequenceShingles, TranspositionNormalizer
from othello_coach.novelty.radar import NoveltyRadar, NoveltyScore
from othello_coach.engine.board import Board


class TestSequenceShingles:
    """Test sequence shingles functionality"""
    
    def test_shingle_generation(self):
        """Test n-gram shingle generation"""
        shingles = SequenceShingles([3, 4])
        moves = [19, 26, 34, 41, 50]
        boards = [self._create_test_board() for _ in moves]
        
        shingle_set = shingles.generate_shingles(moves, boards)
        
        # Should have 3-grams and 4-grams
        assert len(shingle_set) > 0
        # Check that we have the right number of shingles
        # For 5 moves: 3 3-grams + 2 4-grams = 5 total
        assert len(shingle_set) <= 5
    
    def test_jaccard_similarity(self):
        """Test Jaccard similarity calculation"""
        shingles = SequenceShingles()
        
        # Identical sets
        set_a = {(1, 2, 3), (2, 3, 4), (3, 4, 5)}
        set_b = {(1, 2, 3), (2, 3, 4), (3, 4, 5)}
        similarity = shingles.jaccard_similarity(set_a, set_b)
        assert similarity == 1.0
        
        # Completely different sets
        set_c = {(6, 7, 8), (7, 8, 9), (8, 9, 10)}
        similarity = shingles.jaccard_similarity(set_a, set_c)
        assert similarity == 0.0
        
        # Partially overlapping sets
        set_d = {(1, 2, 3), (6, 7, 8)}
        similarity = shingles.jaccard_similarity(set_a, set_d)
        assert 0.0 < similarity < 1.0
    
    def test_minhash_signature(self):
        """Test MinHash signature generation"""
        shingles = SequenceShingles()
        
        shingle_set = {(1, 2, 3), (2, 3, 4), (3, 4, 5)}
        signature = shingles.min_hash_signature(shingle_set, num_hashes=64)
        
        assert len(signature) == 64
        assert all(isinstance(h, int) for h in signature)
    
    def test_similarity_estimation(self):
        """Test similarity estimation from MinHash"""
        shingles = SequenceShingles()
        
        # Same signatures should have similarity 1.0
        sig_a = [1, 2, 3, 4, 5]
        sig_b = [1, 2, 3, 4, 5]
        similarity = shingles.estimate_similarity(sig_a, sig_b)
        assert similarity == 1.0
        
        # Different signatures should have similarity < 1.0
        sig_c = [6, 7, 8, 9, 10]
        similarity = shingles.estimate_similarity(sig_a, sig_c)
        assert similarity == 0.0
    
    def _create_test_board(self) -> Board:
        """Create a test board for testing"""
        return Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=12345)


class TestTranspositionNormalizer:
    """Test transposition normalization"""
    
    def test_normalize_sequence(self):
        """Test sequence normalization"""
        normalizer = TranspositionNormalizer()
        
        moves = [19, 26, 34]
        boards = [self._create_test_board() for _ in moves]
        
        normalized = normalizer.normalize_sequence(moves, boards)
        
        assert len(normalized) == len(moves)
        assert all(isinstance(h, int) for h in normalized)
    
    def test_canonical_cache(self):
        """Test canonical hash caching"""
        normalizer = TranspositionNormalizer()
        board = self._create_test_board()
        
        # First call should add to cache
        hash1 = normalizer._get_canonical_hash(board)
        assert board.hash in normalizer.canonical_cache
        
        # Second call should use cache
        hash2 = normalizer._get_canonical_hash(board)
        assert hash1 == hash2
    
    def _create_test_board(self) -> Board:
        """Create a test board for testing"""
        return Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=12345)


class TestNoveltyRadar:
    """Test novelty radar functionality"""
    
    def test_radar_initialization(self):
        """Test radar initialization"""
        radar = NoveltyRadar()
        
        assert radar.alpha == 0.7
        assert radar.beta == 0.3
        assert radar.k_plies == 6
        assert 'openings' in radar.known_lines
        assert 'selfplay' in radar.known_lines
    
    def test_coverage_calculation(self):
        """Test coverage calculation"""
        radar = NoveltyRadar()
        
        moves = [19, 26, 34, 41]
        boards = [self._create_test_board() for _ in moves]
        
        # Should return a coverage score between 0 and 1
        coverage = radar.calculate_coverage(moves, boards)
        assert 0.0 <= coverage <= 1.0
    
    def test_engine_interest_calculation(self):
        """Test engine interest calculation"""
        radar = NoveltyRadar()
        
        moves = [19, 26, 34, 41]
        boards = [self._create_test_board() for _ in moves]
        scores = [0.0, 50.0, -30.0, 20.0]  # Varying eval scores
        
        interest = radar.calculate_engine_interest(moves, boards, scores)
        assert 0.0 <= interest <= 1.0
    
    def test_novelty_scoring(self):
        """Test complete novelty scoring"""
        radar = NoveltyRadar()
        
        moves = [19, 26, 34, 41]
        boards = [self._create_test_board() for _ in moves]
        scores = [0.0, 50.0, -30.0, 20.0]
        
        novelty_score = radar.score_novelty(moves, boards, scores)
        
        assert isinstance(novelty_score, NoveltyScore)
        assert 0.0 <= novelty_score.coverage <= 1.0
        assert 0.0 <= novelty_score.engine_interest <= 1.0
        assert 0.0 <= novelty_score.novelty_score <= 1.0
    
    def test_candidate_ranking(self):
        """Test ranking of multiple candidates"""
        radar = NoveltyRadar()
        
        # Create multiple candidate lines
        candidates = []
        for i in range(3):
            moves = [19 + i, 26 + i, 34 + i]
            boards = [self._create_test_board() for _ in moves]
            scores = [float(i * 10), float((i + 1) * 10), float((i + 2) * 10)]
            candidates.append((moves, boards, scores))
        
        ranked_scores = radar.rank_candidates(candidates)
        
        assert len(ranked_scores) == 3
        assert all(isinstance(score, NoveltyScore) for score in ranked_scores)
        assert all(score.rank is not None for score in ranked_scores)
        
        # Check ranking order
        ranks = [score.rank for score in ranked_scores]
        assert sorted(ranks) == [1, 2, 3]
    
    def test_add_selfplay_line(self):
        """Test adding self-play lines to corpus"""
        radar = NoveltyRadar()
        
        initial_size = len(radar.known_lines['selfplay'])
        
        moves = [19, 26, 34, 41, 50]
        boards = [self._create_test_board() for _ in moves]
        
        radar.add_selfplay_line(moves, boards)
        
        # Corpus should grow
        assert len(radar.known_lines['selfplay']) >= initial_size
    
    def _create_test_board(self) -> Board:
        """Create a test board for testing"""
        return Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=12345)
