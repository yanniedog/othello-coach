"""Tests for trainer system"""

import pytest
from datetime import date, timedelta
from othello_coach.trainer.scheduler import LeitnerScheduler, TrainerItem
from othello_coach.trainer.tactics import TacticsGenerator, TacticsPuzzle
from othello_coach.trainer.drills import ParityDrills, EndgameDrills
from othello_coach.engine.board import Board


class TestLeitnerScheduler:
    """Test Leitner spaced repetition scheduler"""
    
    def test_scheduler_initialization(self):
        """Test scheduler initialization"""
        scheduler = LeitnerScheduler(":memory:")  # In-memory SQLite for testing
        
        assert scheduler.leitner_days == [1, 3, 7, 14, 30]
        assert scheduler.engine is not None
        assert scheduler.Session is not None
    
    def test_trainer_item_creation(self):
        """Test creating trainer items"""
        item = TrainerItem(
            hash=12345,
            box=1,
            due=date.today(),
            streak=0,
            suspended=False,
            item_type='tactics',
            content={'hash': 12345}
        )
        
        assert item.hash == 12345
        assert item.box == 1
        assert item.item_type == 'tactics'
        assert not item.suspended
    
    def test_position_classification(self):
        """Test position classification for training types"""
        scheduler = LeitnerScheduler(":memory:")
        
        # Endgame position (few pieces)
        item_type = scheduler._classify_position(
            black=0x0000000000001000,  # Few pieces
            white=0x0000000000002000,
            stm=0,
            ply=50
        )
        assert item_type == 'endgame'
        
        # Opening position (many empty squares)
        item_type = scheduler._classify_position(
            black=0x0000000810000000,  # Start position
            white=0x0000001008000000,
            stm=0,
            ply=0
        )
        assert item_type == 'parity'
    
    def test_daily_queue_empty(self):
        """Test getting daily queue when empty"""
        scheduler = LeitnerScheduler(":memory:")
        
        # Create schema first
        with scheduler.Session() as session:
            session.execute("CREATE TABLE trainer(hash INTEGER PRIMARY KEY, box INTEGER, due DATE, streak INTEGER, suspended INTEGER)")
            session.execute("CREATE TABLE positions(hash INTEGER PRIMARY KEY, black INTEGER, white INTEGER, stm INTEGER, ply INTEGER)")
            session.commit()
        
        queue = scheduler.get_daily_queue(max_items=5)
        assert isinstance(queue, list)
        assert len(queue) <= 5


class TestTacticsGenerator:
    """Test tactics puzzle generator"""
    
    def test_generator_initialization(self):
        """Test generator initialization"""
        generator = TacticsGenerator()
        
        assert generator.min_score_gap == 120.0
        assert generator.search_depth == 8
        assert len(generator.HINT_TYPES) > 0
    
    def test_puzzle_creation(self):
        """Test creating a tactics puzzle"""
        generator = TacticsGenerator()
        board = self._create_test_board()
        
        # Note: This may return None if position doesn't meet puzzle criteria
        puzzle = generator.generate_puzzle(board)
        
        if puzzle:
            assert isinstance(puzzle, TacticsPuzzle)
            assert puzzle.position_hash == board.hash
            assert puzzle.best_move is not None
            assert puzzle.difficulty in ['easy', 'medium', 'hard']
            assert puzzle.hint_type in generator.HINT_TYPES
    
    def test_hint_analysis(self):
        """Test hint type analysis"""
        generator = TacticsGenerator()
        board = self._create_test_board()
        
        hint_type, hint_text = generator._analyze_position_for_hint(board, 19)
        
        assert hint_type in generator.HINT_TYPES
        assert isinstance(hint_text, str)
        assert len(hint_text) > 0
    
    def test_difficulty_determination(self):
        """Test difficulty classification"""
        generator = TacticsGenerator()
        
        # Easy puzzle (large score gap, few alternatives)
        difficulty = generator._determine_difficulty(score_gap=400, num_alternatives=2)
        assert difficulty == 'easy'
        
        # Hard puzzle (small score gap, many alternatives)
        difficulty = generator._determine_difficulty(score_gap=150, num_alternatives=8)
        assert difficulty == 'hard'
    
    def test_solution_validation(self):
        """Test solution validation"""
        generator = TacticsGenerator()
        
        # Create a mock puzzle
        puzzle = TacticsPuzzle(
            position_hash=12345,
            board=self._create_test_board(),
            best_move=19,
            best_score=100.0,
            alternatives=[(26, 50.0), (34, 25.0)],
            hint_type='mobility',
            hint_text='Test hint',
            difficulty='medium'
        )
        
        # Test correct answer
        result = generator.validate_solution(puzzle, 19)
        assert result['correct'] is True
        assert 'Correct!' in result['explanation']
        
        # Test incorrect answer
        result = generator.validate_solution(puzzle, 26)
        assert result['correct'] is False
        assert 'Not the best' in result['explanation']
    
    def test_square_name_conversion(self):
        """Test square index to algebraic notation"""
        generator = TacticsGenerator()
        
        assert generator._square_name(0) == 'a1'
        assert generator._square_name(7) == 'h1'
        assert generator._square_name(56) == 'a8'
        assert generator._square_name(63) == 'h8'
        assert generator._square_name(19) == 'd3'
    
    def _create_test_board(self) -> Board:
        """Create a test board"""
        return Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=12345)


class TestParityDrills:
    """Test parity drill system"""
    
    def test_drill_generation(self):
        """Test generating parity drills"""
        drills = ParityDrills()
        board = self._create_test_board()
        
        # Note: May return None if position doesn't have suitable parity regions
        drill = drills.generate_drill(board)
        
        if drill:
            assert drill.position_hash == board.hash
            assert drill.target_region > 0
            assert len(drill.correct_moves) > 0
            assert len(drill.explanation) > 0
    
    def test_parity_preservation_check(self):
        """Test parity preservation logic"""
        drills = ParityDrills()
        board = self._create_test_board()
        
        # Test with a dummy region mask
        preserves = drills._preserves_parity(board, 19, 0xFF00000000000000)
        assert isinstance(preserves, bool)
    
    def test_solution_validation(self):
        """Test drill solution validation"""
        drills = ParityDrills()
        
        # Create mock drill
        from othello_coach.trainer.drills import ParityDrill
        drill = ParityDrill(
            position_hash=12345,
            board=self._create_test_board(),
            target_region=0xFF00000000000000,
            correct_moves=[19, 26],
            explanation="Test explanation"
        )
        
        # Test correct answer
        result = drills.validate_solution(drill, 19)
        assert result['correct'] is True
        assert 'Correct!' in result['feedback']
        
        # Test incorrect answer
        result = drills.validate_solution(drill, 34)
        assert result['correct'] is False
        assert 'Incorrect' in result['feedback']
    
    def _create_test_board(self) -> Board:
        """Create a test board"""
        return Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=12345)


class TestEndgameDrills:
    """Test endgame drill system"""
    
    def test_drill_generation(self):
        """Test generating endgame drills"""
        drills = EndgameDrills(max_empties=16)
        
        # Create an endgame-like position (simplified)
        board = self._create_endgame_board()
        
        # Note: May return None if position doesn't meet criteria
        drill = drills.generate_drill(board)
        
        if drill:
            assert drill.position_hash == board.hash
            assert drill.empties <= 16
            assert drill.best_move is not None
            assert drill.time_limit > 0
    
    def test_critical_position_check(self):
        """Test critical position identification"""
        drills = EndgameDrills()
        board = self._create_endgame_board()
        
        is_critical = drills._is_critical_position(board, 19, 2.0)
        assert isinstance(is_critical, bool)
    
    def test_solution_validation(self):
        """Test endgame drill solution validation"""
        drills = EndgameDrills()
        
        # Create mock drill
        from othello_coach.trainer.drills import EndgameDrill
        drill = EndgameDrill(
            position_hash=12345,
            board=self._create_endgame_board(),
            empties=12,
            best_move=19,
            exact_score=2.0,
            time_limit=10
        )
        
        # Test correct answer within time
        result = drills.validate_solution(drill, 19, time_taken=5.0)
        assert result['correct'] is True
        assert 'Perfect!' in result['feedback']
        assert result['time_bonus'] > 0
        
        # Test incorrect answer
        result = drills.validate_solution(drill, 26, time_taken=15.0)
        assert result['correct'] is False
        assert 'Incorrect' in result['feedback']
    
    def _create_endgame_board(self) -> Board:
        """Create an endgame-like test board"""
        # Simplified endgame position with fewer pieces
        return Board(
            B=0x0000000000001000,  # Few black pieces
            W=0x0000000000002000,  # Few white pieces  
            stm=0,
            ply=50,
            hash=54321
        )
