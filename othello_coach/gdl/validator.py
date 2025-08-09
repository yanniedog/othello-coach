"""GDL Validator for syntax and semantic checking"""

from typing import List, Dict, Any
from .ast_nodes import GDLProgram, GDLGoal, GDLParams


class ValidationError(Exception):
    """Validation error"""
    pass


class GDLValidator:
    """Validates GDL programs for correctness"""
    
    VALID_FEATURES = {
        'mobility', 'parity', 'stability', 'frontier', 'corners'
    }
    
    VALID_SIDES = {
        'white', 'black', 'stm'
    }
    
    VALID_PREFERENCES = {
        'corners', 'stability', 'mobility'
    }
    
    def validate(self, program: GDLProgram) -> List[str]:
        """Validate a GDL program and return list of errors"""
        errors = []
        
        # Check version
        if program.gdl_v != 1:
            errors.append(f"Unsupported GDL version: {program.gdl_v}")
        
        # Validate goal
        try:
            self._validate_goal(program.goal)
        except ValidationError as e:
            errors.append(str(e))
        
        # Validate params
        if program.params:
            try:
                self._validate_params(program.params)
            except ValidationError as e:
                errors.append(str(e))
        
        return errors
    
    def _validate_goal(self, goal: GDLGoal) -> None:
        """Validate goal definition"""
        if goal.goal_type == 'score':
            if hasattr(goal, 'side') and goal.side not in self.VALID_SIDES:
                raise ValidationError(f"Invalid side: {goal.side}")
        
        elif goal.goal_type == 'earliest_corner':
            if hasattr(goal, 'max_plies') and goal.max_plies < 1:
                raise ValidationError("max_plies must be >= 1")
        
        elif goal.goal_type == 'custom':
            if not hasattr(goal, 'weights') or not goal.weights:
                raise ValidationError("Custom goal must have weights")
            
            for feature in goal.weights:
                if feature not in self.VALID_FEATURES:
                    raise ValidationError(f"Unknown feature: {feature}")
            
            # Check for reasonable weight ranges
            for feature, weight in goal.weights.items():
                if not isinstance(weight, (int, float)):
                    raise ValidationError(f"Weight for {feature} must be numeric")
                if abs(weight) > 10.0:
                    raise ValidationError(f"Weight for {feature} seems excessive: {weight}")
    
    def _validate_params(self, params: GDLParams) -> None:
        """Validate parameter settings"""
        if params.max_depth < 1 or params.max_depth > 20:
            raise ValidationError(f"max_depth must be 1-20, got {params.max_depth}")
        
        if params.width < 1 or params.width > 50:
            raise ValidationError(f"width must be 1-50, got {params.width}")
        
        if params.prefer and params.prefer not in self.VALID_PREFERENCES:
            raise ValidationError(f"Invalid prefer value: {params.prefer}")
        
        if params.weights:
            for name, weight in params.weights.items():
                if not isinstance(weight, (int, float)):
                    raise ValidationError(f"Weight {name} must be numeric")
                if abs(weight) > 10.0:
                    raise ValidationError(f"Weight {name} seems excessive: {weight}")


def validate_gdl_program(program: GDLProgram) -> List[str]:
    """Convenience function to validate a GDL program"""
    validator = GDLValidator()
    return validator.validate(program)
