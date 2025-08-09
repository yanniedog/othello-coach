"""Tests for gauntlet and Glicko-2 system"""

import pytest
from datetime import datetime
from othello_coach.gauntlet.glicko import GlickoRating, GlickoCalculator
from othello_coach.gauntlet.gauntlet import GauntletRunner, GauntletMatch
from othello_coach.gauntlet.calibration import CalibrationManager, CalibrationPoint


class TestGlickoRating:
    """Test Glicko-2 rating system"""
    
    def test_rating_creation(self):
        """Test creating Glicko ratings"""
        rating = GlickoRating(
            rating=1500.0,
            rd=350.0,
            volatility=0.06,
            last_updated=datetime.now(),
            games_played=0
        )
        
        assert rating.rating == 1500.0
        assert rating.rd == 350.0
        assert rating.volatility == 0.06
        assert rating.games_played == 0
    
    def test_confidence_intervals(self):
        """Test confidence interval calculations"""
        rating = GlickoRating(
            rating=1500.0,
            rd=100.0,
            volatility=0.06,
            last_updated=datetime.now()
        )
        
        lower = rating.lower_bound
        upper = rating.upper_bound
        width = rating.confidence_width
        
        assert lower < rating.rating < upper
        assert width == upper - lower
        assert abs(width - 392.0) < 1.0  # 3.92 * 100
    
    def test_glicko_calculator(self):
        """Test Glicko-2 calculator"""
        calc = GlickoCalculator(tau=0.5)
        
        assert calc.tau == 0.5
        assert calc.q > 0
        assert calc.epsilon > 0
    
    def test_initial_rating_creation(self):
        """Test creating initial ratings"""
        calc = GlickoCalculator()
        rating = calc.create_initial_rating()
        
        assert rating.rating == 1500
        assert rating.rd == 350
        assert rating.volatility == 0.06
        assert rating.games_played == 0
    
    def test_rating_update_single_game(self):
        """Test rating update after single game"""
        calc = GlickoCalculator()
        
        player = calc.create_initial_rating()
        opponent = GlickoRating(1400, 30, 0.06, datetime.now())
        
        # Player wins
        updated = calc.update_rating(player, [opponent], [1.0])
        
        assert updated.rating > player.rating  # Should increase after win
        assert updated.rd < player.rd  # Should become more certain
        assert updated.games_played == 1
    
    def test_rating_update_multiple_games(self):
        """Test rating update after multiple games"""
        calc = GlickoCalculator()
        
        player = calc.create_initial_rating()
        opponents = [
            GlickoRating(1400, 30, 0.06, datetime.now()),
            GlickoRating(1550, 100, 0.06, datetime.now()),
            GlickoRating(1700, 300, 0.06, datetime.now())
        ]
        results = [1.0, 0.5, 0.0]  # Win, draw, loss
        
        updated = calc.update_rating(player, opponents, results)
        
        assert updated.games_played == 3
        assert updated.rd < player.rd  # More games = more certainty
    
    def test_win_probability(self):
        """Test win probability calculation"""
        calc = GlickoCalculator()
        
        player = GlickoRating(1600, 200, 0.06, datetime.now())
        opponent = GlickoRating(1400, 200, 0.06, datetime.now())
        
        prob = calc.calculate_win_probability(player, opponent)
        
        assert 0.0 <= prob <= 1.0
        assert prob > 0.5  # Higher rated player should have >50% chance
    
    def test_equal_ratings_win_probability(self):
        """Test win probability for equal ratings"""
        calc = GlickoCalculator()
        
        player = GlickoRating(1500, 200, 0.06, datetime.now())
        opponent = GlickoRating(1500, 200, 0.06, datetime.now())
        
        prob = calc.calculate_win_probability(player, opponent)
        
        assert abs(prob - 0.5) < 0.1  # Should be close to 50%


class TestGauntletMatch:
    """Test gauntlet match functionality"""
    
    def test_match_creation(self):
        """Test creating gauntlet matches"""
        white_rating = GlickoRating(1500, 200, 0.06, datetime.now())
        black_rating = GlickoRating(1400, 150, 0.06, datetime.now())
        
        match = GauntletMatch(
            white_profile="elo_1600",
            black_profile="elo_1400",
            white_rating=white_rating,
            black_rating=black_rating,
            seed=12345
        )
        
        assert match.white_profile == "elo_1600"
        assert match.black_profile == "elo_1400"
        assert match.seed == 12345
        assert match.result is None  # Not played yet
    
    def test_match_completion(self):
        """Test completing a match"""
        white_rating = GlickoRating(1500, 200, 0.06, datetime.now())
        black_rating = GlickoRating(1400, 150, 0.06, datetime.now())
        
        match = GauntletMatch(
            white_profile="elo_1600",
            black_profile="elo_1400",
            white_rating=white_rating,
            black_rating=black_rating
        )
        
        # Simulate completed match
        match.result = 1.0  # White wins
        match.moves = [19, 26, 34, 41]
        match.game_length = 4
        match.started_at = datetime.now()
        match.finished_at = datetime.now()
        
        assert match.result == 1.0
        assert len(match.moves) == 4
        assert match.game_length == 4
        assert match.started_at is not None
        assert match.finished_at is not None


class TestGauntletRunner:
    """Test gauntlet runner (limited due to complexity)"""
    
    def test_runner_initialization(self):
        """Test gauntlet runner initialization"""
        # Use in-memory database for testing
        runner = GauntletRunner(":memory:")
        
        assert runner.engine_version == "1.1.0"
        assert runner.glicko is not None
        assert isinstance(runner.ladder, dict)
    
    def test_ladder_loading(self):
        """Test loading ladder standings"""
        runner = GauntletRunner(":memory:")
        
        # Should have default profiles
        expected_profiles = ['elo_400', 'elo_800', 'elo_1400', 'elo_2000', 'elo_2300', 'max']
        for profile in expected_profiles:
            assert profile in runner.ladder
            assert isinstance(runner.ladder[profile], GlickoRating)
    
    def test_ladder_standings(self):
        """Test getting ladder standings"""
        runner = GauntletRunner(":memory:")
        
        standings = runner.get_ladder_standings()
        
        assert isinstance(standings, list)
        assert len(standings) > 0
        
        # Should be sorted by rating (descending)
        ratings = [rating.rating for profile, rating in standings]
        assert ratings == sorted(ratings, reverse=True)


class TestCalibrationManager:
    """Test calibration system"""
    
    def test_calibration_point_creation(self):
        """Test creating calibration points"""
        point = CalibrationPoint(
            depth=8,
            elo_estimate=1600.0,
            confidence_interval=(1550.0, 1650.0),
            games_played=100,
            last_updated=datetime.now()
        )
        
        assert point.depth == 8
        assert point.elo_estimate == 1600.0
        assert point.confidence_interval == (1550.0, 1650.0)
        assert point.games_played == 100
    
    def test_depth_extraction(self):
        """Test extracting depth from profile names"""
        manager = CalibrationManager(":memory:")
        
        # Standard profiles
        assert manager._extract_depth_from_profile("elo_400") == 2
        assert manager._extract_depth_from_profile("elo_1600") == None  # Not in standard map
        assert manager._extract_depth_from_profile("max") == 14
        
        # Custom depth profiles
        assert manager._extract_depth_from_profile("depth_10") == 10
        assert manager._extract_depth_from_profile("depth_6") == 6
    
    def test_elo_interpolation(self):
        """Test ELO interpolation for missing depths"""
        manager = CalibrationManager(":memory:")
        
        # Add some test calibration points
        manager.depth_elo_mapping[4] = CalibrationPoint(
            depth=4, elo_estimate=1200.0, confidence_interval=(1150, 1250),
            games_played=100, last_updated=datetime.now()
        )
        manager.depth_elo_mapping[8] = CalibrationPoint(
            depth=8, elo_estimate=1600.0, confidence_interval=(1550, 1650),
            games_played=100, last_updated=datetime.now()
        )
        
        # Test interpolation
        result = manager._interpolate_elo(6)
        if result:
            elo, ci = result
            assert 1200.0 < elo < 1600.0  # Should be between the bounds
            assert ci[0] < elo < ci[1]  # Should be within confidence interval
    
    def test_win_probability_calibration(self):
        """Test win probability calibration"""
        manager = CalibrationManager(":memory:")
        
        # Create sample game data (score, outcome pairs)
        game_data = [
            (100.0, 1.0),  # +100cp, win
            (50.0, 1.0),   # +50cp, win
            (0.0, 0.5),    # 0cp, draw
            (-50.0, 0.0),  # -50cp, loss
            (-100.0, 0.0)  # -100cp, loss
        ]
        
        # Note: This test may fail if scipy is not available
        try:
            manager.calibrate_win_probability(game_data)
            
            if manager.win_prob_calibration:
                assert manager.win_prob_calibration.samples == len(game_data)
                assert manager.win_prob_calibration.r_squared is not None
        except ImportError:
            pytest.skip("scipy not available for win probability calibration")
    
    def test_get_win_probability(self):
        """Test getting win probability from score"""
        manager = CalibrationManager(":memory:")
        
        # Without calibration, should return None
        prob = manager.get_win_probability(50.0)
        assert prob is None
        
        # With mock calibration
        from othello_coach.gauntlet.calibration import WinProbCalibration
        manager.win_prob_calibration = WinProbCalibration(
            a=0.0, b=0.01, r_squared=0.8, samples=100, last_updated=datetime.now()
        )
        
        prob = manager.get_win_probability(50.0)
        assert prob is not None
        assert 0.0 <= prob <= 1.0
