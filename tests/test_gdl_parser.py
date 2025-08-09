"""Tests for GDL parser and AST"""

import pytest
from othello_coach.gdl.parser import GDLParser, GDLParseError
from othello_coach.gdl.ast_nodes import *


class TestGDLParser:
    """Test GDL parser functionality"""
    
    def test_parse_score_goal(self):
        """Test parsing score goals"""
        parser = GDLParser()
        
        # Test basic score goal
        program = parser.parse("score(side=white)")
        assert isinstance(program.goal, ScoreGoal)
        assert program.goal.side == "white"
        assert program.gdl_v == 1
        
        # Test with different sides
        program = parser.parse("score(side=black)")
        assert program.goal.side == "black"
        
        program = parser.parse("score(side=stm)")
        assert program.goal.side == "stm"
    
    def test_parse_min_opp_mob(self):
        """Test parsing min_opp_mob goal"""
        parser = GDLParser()
        program = parser.parse("min_opp_mob")
        
        assert isinstance(program.goal, MinOppMobGoal)
        assert program.goal.goal_type == "min_opp_mob"
    
    def test_parse_earliest_corner(self):
        """Test parsing earliest_corner goal"""
        parser = GDLParser()
        program = parser.parse("earliest_corner(max_plies=4)")
        
        assert isinstance(program.goal, EarliestCornerGoal)
        assert program.goal.max_plies == 4
    
    def test_parse_max_stability(self):
        """Test parsing max_stability goal"""
        parser = GDLParser()
        program = parser.parse("max_stability")
        
        assert isinstance(program.goal, MaxStabilityGoal)
        assert program.goal.goal_type == "max_stability"
    
    def test_parse_custom_goal(self):
        """Test parsing custom weighted goals"""
        parser = GDLParser()
        program = parser.parse("custom(weights={mobility:0.5, parity:0.3, stability:0.2})")
        
        assert isinstance(program.goal, CustomGoal)
        assert program.goal.weights == {
            'mobility': 0.5,
            'parity': 0.3,
            'stability': 0.2
        }
    
    def test_parse_with_parameters(self):
        """Test parsing goals with parameters"""
        parser = GDLParser()
        program = parser.parse("""
            score(side=white)
            max_depth=10
            width=15
            prefer=corners
        """)
        
        assert isinstance(program.goal, ScoreGoal)
        assert program.params.max_depth == 10
        assert program.params.width == 15
        assert program.params.prefer == "corners"
    
    def test_parse_with_weights(self):
        """Test parsing with weight parameters"""
        parser = GDLParser()
        program = parser.parse("""
            min_opp_mob
            weight(parity=0.8)
            weight(mobility=0.2)
        """)
        
        assert isinstance(program.goal, MinOppMobGoal)
        assert program.params.weights == {
            'parity': 0.8,
            'mobility': 0.2
        }
    
    def test_parse_errors(self):
        """Test parser error handling"""
        parser = GDLParser()
        
        # Invalid goal type
        with pytest.raises(GDLParseError):
            parser.parse("invalid_goal")
        
        # Invalid side
        with pytest.raises(GDLParseError):
            parser.parse("score(side=invalid)")
        
        # Missing max_plies
        with pytest.raises(GDLParseError):
            parser.parse("earliest_corner()")
        
        # Invalid max_plies
        with pytest.raises(GDLParseError):
            parser.parse("earliest_corner(max_plies=0)")
        
        # Empty custom weights
        with pytest.raises(GDLParseError):
            parser.parse("custom(weights={})")
    
    def test_serialization(self):
        """Test AST serialization/deserialization"""
        parser = GDLParser()
        original = parser.parse("""
            custom(weights={mobility:0.6, corners:0.4})
            max_depth=8
            width=12
            prefer=stability
        """)
        
        # Serialize to dict
        data = original.to_dict()
        assert data['gdl_v'] == 1
        assert data['goal']['type'] == 'custom'
        assert data['params']['max_depth'] == 8
        
        # Deserialize back
        restored = GDLProgram.from_dict(data)
        assert isinstance(restored.goal, CustomGoal)
        assert restored.goal.weights == original.goal.weights
        assert restored.params.max_depth == original.params.max_depth
        assert restored.params.prefer == original.params.prefer
    
    def test_json_serialization(self):
        """Test JSON serialization"""
        parser = GDLParser()
        program = parser.parse("score(side=black) max_depth=6")
        
        # To JSON
        json_str = program.to_json()
        assert isinstance(json_str, str)
        assert 'score' in json_str
        assert 'black' in json_str
        
        # From JSON
        restored = GDLProgram.from_json(json_str)
        assert isinstance(restored.goal, ScoreGoal)
        assert restored.goal.side == "black"
        assert restored.params.max_depth == 6


class TestGDLValidation:
    """Test GDL validation"""
    
    def test_valid_programs(self):
        """Test validation of valid programs"""
        from othello_coach.gdl.validator import validate_gdl_program
        
        parser = GDLParser()
        
        # Valid basic program
        program = parser.parse("score(side=white)")
        errors = validate_gdl_program(program)
        assert len(errors) == 0
        
        # Valid complex program
        program = parser.parse("""
            custom(weights={mobility:0.5, stability:0.3, parity:0.2})
            max_depth=8
            width=12
            prefer=corners
        """)
        errors = validate_gdl_program(program)
        assert len(errors) == 0
    
    def test_invalid_programs(self):
        """Test validation of invalid programs"""
        from othello_coach.gdl.validator import validate_gdl_program
        
        # Create invalid program manually (parser would catch syntax errors)
        goal = CustomGoal(goal_type='custom', weights={'invalid_feature': 1.0})
        program = GDLProgram(gdl_v=1, goal=goal)
        
        errors = validate_gdl_program(program)
        assert len(errors) > 0
        assert 'Unknown feature' in errors[0]
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        from othello_coach.gdl.validator import validate_gdl_program
        
        # Invalid depth
        goal = ScoreGoal(goal_type='score', side='white')
        params = GDLParams(max_depth=0)  # Invalid
        program = GDLProgram(gdl_v=1, goal=goal, params=params)
        
        errors = validate_gdl_program(program)
        assert len(errors) > 0
        assert 'max_depth' in errors[0]
