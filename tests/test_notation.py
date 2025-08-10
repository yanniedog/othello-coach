"""
Tests for the coordinate notation system.
"""

import pytest
from othello_coach.engine.notation import (
    coord_to_notation,
    notation_to_coord,
    moves_to_string,
    string_to_moves,
    is_valid_notation,
    get_coordinate_description,
    get_notation_description,
    format_moves_with_passes,
    PASS_NOTATION
)


class TestCoordinateNotation:
    """Test coordinate notation conversion functions."""
    
    def test_coord_to_notation(self):
        """Test converting coordinates to notation."""
        # Test corner positions
        assert coord_to_notation(0) == "a1"   # Top-left
        assert coord_to_notation(7) == "h1"   # Top-right
        assert coord_to_notation(56) == "a8"  # Bottom-left
        assert coord_to_notation(63) == "h8"  # Bottom-right
        
        # Test center positions
        assert coord_to_notation(27) == "d4"  # Center-left
        assert coord_to_notation(28) == "e4"  # Center-right
        assert coord_to_notation(35) == "d5"  # Center-left
        assert coord_to_notation(36) == "e5"  # Center-right
        
        # Test edge positions
        assert coord_to_notation(8) == "a2"   # Left edge
        assert coord_to_notation(15) == "h2"  # Right edge
        assert coord_to_notation(48) == "a7"  # Left edge
        assert coord_to_notation(55) == "h7"  # Right edge
    
    def test_notation_to_coord(self):
        """Test converting notation to coordinates."""
        # Test corner positions
        assert notation_to_coord("a1") == 0
        assert notation_to_coord("h1") == 7
        assert notation_to_coord("a8") == 56
        assert notation_to_coord("h8") == 63
        
        # Test center positions
        assert notation_to_coord("d4") == 27
        assert notation_to_coord("e4") == 28
        assert notation_to_coord("d5") == 35
        assert notation_to_coord("e5") == 36
        
        # Test case insensitivity
        assert notation_to_coord("A1") == 0
        assert notation_to_coord("H8") == 63
    
    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        with pytest.raises(ValueError):
            coord_to_notation(-1)
        with pytest.raises(ValueError):
            coord_to_notation(64)
        with pytest.raises(ValueError):
            coord_to_notation(100)
    
    def test_invalid_notation(self):
        """Test handling of invalid notation."""
        with pytest.raises(ValueError):
            notation_to_coord("x9")  # Invalid file
        with pytest.raises(ValueError):
            notation_to_coord("a9")  # Invalid rank
        with pytest.raises(ValueError):
            notation_to_coord("i1")  # Invalid file
        with pytest.raises(ValueError):
            notation_to_coord("a0")  # Invalid rank
        with pytest.raises(ValueError):
            notation_to_coord("abc")  # Too long
        with pytest.raises(ValueError):
            notation_to_coord("1a")   # Wrong order
        with pytest.raises(ValueError):
            notation_to_coord("")     # Empty string


class TestMovesStringConversion:
    """Test converting between moves lists and notation strings."""
    
    def test_moves_to_string(self):
        """Test converting moves list to notation string."""
        moves = [19, 26, 34, 37]  # d3, c4, c5, f5
        expected = "d3c4c5f5"
        assert moves_to_string(moves) == expected
        
        # Test empty list
        assert moves_to_string([]) == ""
        
        # Test single move
        assert moves_to_string([27]) == "d4"
    
    def test_string_to_moves(self):
        """Test converting notation string to moves list."""
        moves_str = "d3c4c5f5"
        expected = [19, 26, 34, 37]  # d3, c4, c5, f5
        assert string_to_moves(moves_str) == expected
        
        # Test empty string
        assert string_to_moves("") == []
        
        # Test single move
        assert string_to_moves("d4") == [27]
    
    def test_string_to_moves_with_passes(self):
        """Test converting notation string with pass moves."""
        moves_str = "d3--c4--f5"
        expected = [19, -1, 26, -1, 37]  # d3, pass, c4, pass, f5
        assert string_to_moves(moves_str) == expected
        
        # Test consecutive passes
        moves_str = "d3----c4"
        expected = [19, -1, -1, 26]  # d3, pass, pass, c4
        assert string_to_moves(moves_str) == expected
    
    def test_invalid_string_handling(self):
        """Test handling of invalid notation strings."""
        # Test incomplete notation at end
        moves_str = "d3c4c"
        expected = [19, 26]  # d3, c4 (c is incomplete, so skipped)
        assert string_to_moves(moves_str) == expected
        
        # Test mixed valid/invalid
        moves_str = "d3x9c4"
        expected = [19, 26]  # d3, c4 (x9 is invalid, so skipped)
        assert string_to_moves(moves_str) == expected


class TestPassMoveHandling:
    """Test handling of pass moves."""
    
    def test_format_moves_with_passes(self):
        """Test formatting moves with pass information."""
        moves = [19, 26, 34, 37]  # d3, c4, c5, f5
        passes = [1, 2]  # Pass after move 1 and 2
        
        # Expected: d3, c4, pass, c5, pass, f5
        expected = "d3c4--c5--f5"
        assert format_moves_with_passes(moves, passes) == expected
        
        # Test no passes
        assert format_moves_with_passes(moves, []) == "d3c4c5f5"
        
        # Test only passes
        assert format_moves_with_passes([], [0, 1]) == "----"
        
        # Test empty lists
        assert format_moves_with_passes([], []) == ""
    
    def test_pass_notation_constant(self):
        """Test pass notation constant."""
        assert PASS_NOTATION == "--"


class TestValidation:
    """Test notation validation functions."""
    
    def test_is_valid_notation(self):
        """Test notation validation."""
        # Valid notations
        assert is_valid_notation("")
        assert is_valid_notation("d3")
        assert is_valid_notation("d3c4c5f5")
        assert is_valid_notation("d3--c4")
        assert is_valid_notation("----")
        
        # Invalid notations
        assert not is_valid_notation("d3c")  # Incomplete
        assert not is_valid_notation("d3x9")  # Invalid move
        assert not is_valid_notation("d3-c4")  # Single dash
        assert not is_valid_notation("d3---c4")  # Three dashes


class TestDescriptions:
    """Test coordinate and notation description functions."""
    
    def test_get_coordinate_description(self):
        """Test getting coordinate descriptions."""
        assert get_coordinate_description(0) == "a1"
        assert get_coordinate_description(27) == "d4"
        assert get_coordinate_description(63) == "h8"
        assert get_coordinate_description(-1) == "invalid"
        assert get_coordinate_description(64) == "invalid"
    
    def test_get_notation_description(self):
        """Test getting notation descriptions."""
        assert get_notation_description("d4") == "d4"
        assert get_notation_description("--") == "pass"
        assert get_notation_description("x9") == "invalid"
        assert get_notation_description("") == "invalid"


class TestRealGameScenarios:
    """Test real game scenarios with the notation system."""
    
    def test_typical_opening_moves(self):
        """Test typical opening move sequences."""
        # Common opening moves: d3, c4, c5, f5
        moves = [19, 26, 34, 37]
        moves_str = moves_to_string(moves)
        assert moves_str == "d3c4c5f5"
        
        # Convert back
        converted_moves = string_to_moves(moves_str)
        assert converted_moves == moves
    
    def test_game_with_passes(self):
        """Test a game that includes pass moves."""
        moves = [19, 26, 34]  # d3, c4, c5
        passes = [2]  # Pass after move 2
        
        moves_str = format_moves_with_passes(moves, passes)
        assert moves_str == "d3c4c5--"
        
        # Convert back (passes become -1)
        converted_moves = string_to_moves(moves_str)
        assert converted_moves == [19, 26, 34, -1]
    
    def test_edge_case_positions(self):
        """Test edge case board positions."""
        # Test all corners
        corner_moves = [0, 7, 56, 63]  # a1, h1, a8, h8
        moves_str = moves_to_string(corner_moves)
        assert moves_str == "a1h1a8h8"
        
        # Test center squares
        center_moves = [27, 28, 35, 36]  # d4, e4, d5, e5
        moves_str = moves_to_string(center_moves)
        assert moves_str == "d4e4d5e5"
