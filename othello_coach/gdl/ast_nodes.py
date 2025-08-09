"""GDL AST node definitions"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import orjson


@dataclass
class GDLGoal:
    """Base class for GDL goals"""
    goal_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        raise NotImplementedError
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GDLGoal':
        """Create from dictionary"""
        goal_type = data.get('type')
        if goal_type == 'score':
            return ScoreGoal.from_dict(data)
        elif goal_type == 'min_opp_mob':
            return MinOppMobGoal.from_dict(data)
        elif goal_type == 'earliest_corner':
            return EarliestCornerGoal.from_dict(data)
        elif goal_type == 'max_stability':
            return MaxStabilityGoal.from_dict(data)
        elif goal_type == 'custom':
            return CustomGoal.from_dict(data)
        else:
            raise ValueError(f"Unknown goal type: {goal_type}")


@dataclass
class ScoreGoal(GDLGoal):
    """Maximize eval for a specific side"""
    side: str  # 'white', 'black', 'stm'
    
    def __post_init__(self):
        self.goal_type = 'score'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'score',
            'side': self.side
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScoreGoal':
        return cls(side=data['side'])


@dataclass
class MinOppMobGoal(GDLGoal):
    """Minimize opponent's next-move count"""
    
    def __post_init__(self):
        self.goal_type = 'min_opp_mob'
    
    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'min_opp_mob'}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinOppMobGoal':
        return cls()


@dataclass
class EarliestCornerGoal(GDLGoal):
    """Reward early corner capture"""
    max_plies: int
    
    def __post_init__(self):
        self.goal_type = 'earliest_corner'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'earliest_corner',
            'max_plies': self.max_plies
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EarliestCornerGoal':
        return cls(max_plies=data['max_plies'])


@dataclass
class MaxStabilityGoal(GDLGoal):
    """Maximize stability"""
    
    def __post_init__(self):
        self.goal_type = 'max_stability'
    
    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'max_stability'}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaxStabilityGoal':
        return cls()


@dataclass
class CustomGoal(GDLGoal):
    """Custom weighted feature combination"""
    weights: Dict[str, float]
    
    def __post_init__(self):
        self.goal_type = 'custom'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'custom',
            'weights': self.weights
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomGoal':
        return cls(weights=data['weights'])


@dataclass
class GDLParams:
    """GDL parameter settings"""
    max_depth: int = 8
    width: int = 12
    prefer: Optional[str] = None  # 'corners', 'stability', 'mobility'
    weights: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'max_depth': self.max_depth,
            'width': self.width
        }
        if self.prefer:
            result['prefer'] = self.prefer
        if self.weights:
            result['weights'] = self.weights
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GDLParams':
        return cls(
            max_depth=data.get('max_depth', 8),
            width=data.get('width', 12),
            prefer=data.get('prefer'),
            weights=data.get('weights')
        )


@dataclass
class GDLProgram:
    """Complete GDL program"""
    gdl_v: int
    goal: GDLGoal
    params: Optional[GDLParams] = None
    source: Optional[str] = None
    
    def __post_init__(self):
        if self.params is None:
            self.params = GDLParams()
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'gdl_v': self.gdl_v,
            'goal': self.goal.to_dict()
        }
        if self.params:
            result['params'] = self.params.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GDLProgram':
        goal = GDLGoal.from_dict(data['goal'])
        params = None
        if 'params' in data:
            params = GDLParams.from_dict(data['params'])
        return cls(
            gdl_v=data['gdl_v'],
            goal=goal,
            params=params,
            source=data.get('source')
        )
    
    def to_json(self) -> str:
        """Serialize to JSON string"""
        return orjson.dumps(self.to_dict()).decode('utf-8')
    
    @classmethod
    def from_json(cls, json_str: str) -> 'GDLProgram':
        """Deserialize from JSON string"""
        data = orjson.loads(json_str)
        return cls.from_dict(data)
