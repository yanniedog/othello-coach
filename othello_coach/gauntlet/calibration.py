"""Calibration manager for depth-ELO mapping and win probability"""

import json
import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass
# Note: Using standard library instead of numpy/scipy for simpler dependencies
from .glicko import GlickoRating


@dataclass
class CalibrationPoint:
    """Single calibration data point"""
    depth: int
    elo_estimate: float
    confidence_interval: Tuple[float, float]
    games_played: int
    last_updated: datetime


@dataclass
class WinProbCalibration:
    """Win probability calibration parameters"""
    a: float  # logistic intercept
    b: float  # logistic slope  
    r_squared: float
    samples: int
    last_updated: datetime


class CalibrationManager:
    """Manages depth-ELO mapping and win probability calibration"""
    
    def __init__(self, db_path: str, engine_version: str = "1.1.0"):
        self.db_path = db_path
        self.engine_version = engine_version
        
        # Load existing calibrations
        self.depth_elo_mapping = self._load_depth_elo_mapping()
        self.win_prob_calibration = self._load_win_prob_calibration()
    
    def _load_depth_elo_mapping(self) -> Dict[int, CalibrationPoint]:
        """Load depth-ELO mapping from database"""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        Session = sessionmaker(bind=engine)
        
        # Ensure schema exists for in-memory databases (used in tests)
        if self.db_path == ":memory:":
            self._ensure_schema(engine)
        
        mapping = {}
        with Session() as session:
            query = text("""
                SELECT json FROM mappings WHERE engine_ver = :engine_ver
            """)
            result = session.execute(query, {'engine_ver': self.engine_version}).fetchone()
            
            if result:
                data = json.loads(result.json)
                for depth_str, point_data in data.get('depth_elo', {}).items():
                    depth = int(depth_str)
                    mapping[depth] = CalibrationPoint(
                        depth=depth,
                        elo_estimate=point_data['elo_estimate'],
                        confidence_interval=tuple(point_data['confidence_interval']),
                        games_played=point_data['games_played'],
                        last_updated=datetime.fromisoformat(point_data['last_updated'])
                    )
        
        return mapping
    
    def _ensure_schema(self, engine):
        """Ensure database schema exists (for tests)"""
        from ..db.schema_sql_loader import get_schema_sql
        # Use raw connection to execute multiple statements
        raw_conn = engine.raw_connection()
        try:
            raw_conn.executescript(get_schema_sql())
        finally:
            raw_conn.close()
    
    def _load_win_prob_calibration(self) -> Optional[WinProbCalibration]:
        """Load win probability calibration from database"""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        Session = sessionmaker(bind=engine)
        
        # Ensure schema exists for in-memory databases (used in tests)
        if self.db_path == ":memory:":
            self._ensure_schema(engine)
        
        with Session() as session:
            query = text("""
                SELECT json FROM mappings WHERE engine_ver = :engine_ver
            """)
            result = session.execute(query, {'engine_ver': self.engine_version}).fetchone()
            
            if result:
                data = json.loads(result.json)
                wp_data = data.get('win_prob_calibration')
                if wp_data:
                    return WinProbCalibration(
                        a=wp_data['a'],
                        b=wp_data['b'],
                        r_squared=wp_data['r_squared'],
                        samples=wp_data['samples'],
                        last_updated=datetime.fromisoformat(wp_data['last_updated'])
                    )
        
        return None
    
    def update_depth_elo_mapping(self, ladder_standings: List[Tuple[str, GlickoRating]]):
        """Update depth-ELO mapping from ladder results"""
        # Extract depth from profile names and map to ratings
        depth_ratings = {}
        
        for profile, rating in ladder_standings:
            # Extract depth from profile (assumes format like "depth_8" or standard profiles)
            depth = self._extract_depth_from_profile(profile)
            if depth:
                if depth not in depth_ratings:
                    depth_ratings[depth] = []
                depth_ratings[depth].append(rating)
        
        # Update mapping for each depth
        for depth, ratings in depth_ratings.items():
            if len(ratings) >= 3:  # Need sufficient data
                mean_rating = sum(r.rating for r in ratings) / len(ratings)
                mean_rd = sum(r.rd for r in ratings) / len(ratings)
                
                # Calculate confidence interval
                ci_half_width = 1.96 * mean_rd / math.sqrt(len(ratings))
                ci = (mean_rating - ci_half_width, mean_rating + ci_half_width)
                
                total_games = sum(r.games_played for r in ratings)
                
                self.depth_elo_mapping[depth] = CalibrationPoint(
                    depth=depth,
                    elo_estimate=mean_rating,
                    confidence_interval=ci,
                    games_played=total_games,
                    last_updated=datetime.now()
                )
        
        # Save updated mapping
        self._save_mappings()
    
    def _extract_depth_from_profile(self, profile: str) -> Optional[int]:
        """Extract search depth from profile name"""
        # Map standard profiles to approximate depths
        standard_depths = {
            'elo_400': 2,
            'elo_800': 4,
            'elo_1400': 6,
            'elo_2000': 9,
            'elo_2300': 12,
            'max': 14
        }
        
        if profile in standard_depths:
            return standard_depths[profile]
        
        # Try to extract from custom depth profiles
        if profile.startswith('depth_'):
            try:
                return int(profile.split('_')[1])
            except (IndexError, ValueError):
                pass
        
        return None
    
    def get_elo_for_depth(self, depth: int) -> Optional[Tuple[float, Tuple[float, float]]]:
        """Get ELO estimate and confidence interval for a given depth"""
        if depth in self.depth_elo_mapping:
            point = self.depth_elo_mapping[depth]
            return point.elo_estimate, point.confidence_interval
        
        # Interpolate if exact depth not available
        return self._interpolate_elo(depth)
    
    def _interpolate_elo(self, target_depth: int) -> Optional[Tuple[float, Tuple[float, float]]]:
        """Interpolate ELO for depths not directly calibrated"""
        if len(self.depth_elo_mapping) < 2:
            return None
        
        depths = sorted(self.depth_elo_mapping.keys())
        
        # Find bracketing depths
        lower_depth = None
        upper_depth = None
        
        for depth in depths:
            if depth <= target_depth:
                lower_depth = depth
            if depth >= target_depth and upper_depth is None:
                upper_depth = depth
        
        if lower_depth is None or upper_depth is None:
            # Extrapolation - use nearest point
            nearest_depth = min(depths, key=lambda d: abs(d - target_depth))
            point = self.depth_elo_mapping[nearest_depth]
            return point.elo_estimate, point.confidence_interval
        
        if lower_depth == upper_depth:
            # Exact match
            point = self.depth_elo_mapping[lower_depth]
            return point.elo_estimate, point.confidence_interval
        
        # Linear interpolation
        lower_point = self.depth_elo_mapping[lower_depth]
        upper_point = self.depth_elo_mapping[upper_depth]
        
        alpha = (target_depth - lower_depth) / (upper_depth - lower_depth)
        interpolated_elo = lower_point.elo_estimate + alpha * (upper_point.elo_estimate - lower_point.elo_estimate)
        
        # Interpolate confidence intervals
        lower_ci_width = lower_point.confidence_interval[1] - lower_point.confidence_interval[0]
        upper_ci_width = upper_point.confidence_interval[1] - upper_point.confidence_interval[0]
        ci_width = lower_ci_width + alpha * (upper_ci_width - lower_ci_width)
        
        ci = (interpolated_elo - ci_width/2, interpolated_elo + ci_width/2)
        
        return interpolated_elo, ci
    
    def calibrate_win_probability(self, game_data: List[Tuple[float, float]]):
        """Calibrate win probability curve from score-outcome pairs
        
        Args:
            game_data: List of (score_cp, actual_result) pairs where result is 0/0.5/1
        """
        if len(game_data) < 50:  # Need sufficient data
            return
        
        scores, outcomes = zip(*game_data)
        scores = list(scores)
        outcomes = list(outcomes)
        
        # Fit logistic regression: P(win) = 1 / (1 + exp(-(a + b * score)))
        def logistic(x, a, b):
            # Simple logistic function using math instead of numpy
            if isinstance(x, (list, tuple)):
                return [1 / (1 + math.exp(-(a + b * xi))) for xi in x]
            else:
                return 1 / (1 + math.exp(-(a + b * x)))
        
        # Simple calibration without scipy optimization
        try:
            # Use basic linear regression as approximation
            n = len(scores)
            if n == 0:
                return
                
            sum_scores = sum(scores)
            sum_outcomes = sum(outcomes)
            sum_scores_sq = sum(s*s for s in scores)
            sum_score_outcome = sum(s*o for s, o in zip(scores, outcomes))
            
            # Linear regression coefficients
            if n * sum_scores_sq - sum_scores * sum_scores != 0:
                b = (n * sum_score_outcome - sum_scores * sum_outcomes) / (n * sum_scores_sq - sum_scores * sum_scores)
                a = (sum_outcomes - b * sum_scores) / n
                
                # Scale for logistic-like behavior
                b = b * 0.01
                
                # Simple R-squared calculation
                mean_outcome = sum_outcomes / n
                predictions = [max(0.01, min(0.99, a + b * s)) for s in scores]
                ss_tot = sum((o - mean_outcome) ** 2 for o in outcomes)
                ss_res = sum((o - p) ** 2 for o, p in zip(outcomes, predictions))
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
                
                self.win_prob_calibration = WinProbCalibration(
                    a=a,
                    b=b,
                    r_squared=max(0.0, r_squared),
                    samples=len(game_data),
                    last_updated=datetime.now()
                )
                
                self._save_mappings()
                
        except Exception as e:
            print(f"Win probability calibration failed: {e}")
    
    def get_win_probability(self, score_cp: float) -> Optional[float]:
        """Get win probability for a given centipawn score"""
        if self.win_prob_calibration is None:
            return None
        
        # P(win) = 1 / (1 + exp(-(a + b * score)))
        linear_combination = self.win_prob_calibration.a + self.win_prob_calibration.b * score_cp
        return 1 / (1 + math.exp(-linear_combination))
    
    def _save_mappings(self):
        """Save calibration data to database"""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Prepare data for serialization
        data = {
            'depth_elo': {},
            'win_prob_calibration': None
        }
        
        for depth, point in self.depth_elo_mapping.items():
            data['depth_elo'][str(depth)] = {
                'elo_estimate': point.elo_estimate,
                'confidence_interval': list(point.confidence_interval),
                'games_played': point.games_played,
                'last_updated': point.last_updated.isoformat()
            }
        
        if self.win_prob_calibration:
            data['win_prob_calibration'] = {
                'a': self.win_prob_calibration.a,
                'b': self.win_prob_calibration.b,
                'r_squared': self.win_prob_calibration.r_squared,
                'samples': self.win_prob_calibration.samples,
                'last_updated': self.win_prob_calibration.last_updated.isoformat()
            }
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            query = text("""
                INSERT OR REPLACE INTO mappings (engine_ver, json, created_at)
                VALUES (:engine_ver, :json, :created_at)
            """)
            session.execute(query, {
                'engine_ver': self.engine_version,
                'json': json.dumps(data),
                'created_at': datetime.now()
            })
            session.commit()
    
    def is_mapping_reliable(self, depth: int) -> bool:
        """Check if depth-ELO mapping is reliable for given depth"""
        if depth not in self.depth_elo_mapping:
            return False
        
        point = self.depth_elo_mapping[depth]
        ci_width = point.confidence_interval[1] - point.confidence_interval[0]
        
        # Mapping is reliable if CI is narrow and we have enough games
        return ci_width < 200 and point.games_played >= 100
