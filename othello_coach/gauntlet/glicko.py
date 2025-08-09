"""Glicko-2 rating system implementation"""

import math
from dataclasses import dataclass
from typing import List, Tuple
from datetime import datetime


@dataclass
class GlickoRating:
    """Glicko-2 rating representation"""
    rating: float  # μ
    rd: float      # φ (rating deviation)
    volatility: float  # σ
    last_updated: datetime
    games_played: int = 0
    
    @property
    def lower_bound(self) -> float:
        """95% confidence interval lower bound"""
        return self.rating - 1.96 * self.rd
    
    @property
    def upper_bound(self) -> float:
        """95% confidence interval upper bound"""
        return self.rating + 1.96 * self.rd
    
    @property
    def confidence_width(self) -> float:
        """Width of 95% confidence interval"""
        return 3.92 * self.rd  # 2 * 1.96 * rd


class GlickoCalculator:
    """Glicko-2 rating calculator"""
    
    def __init__(self, tau: float = 0.5):
        self.tau = tau  # System volatility constraint
        self.q = math.log(10) / 400
        self.epsilon = 0.000001  # Convergence criterion
    
    def create_initial_rating(self, initial_rating: float = 1500, 
                            initial_rd: float = 350, 
                            initial_volatility: float = 0.06) -> GlickoRating:
        """Create initial Glicko-2 rating"""
        return GlickoRating(
            rating=initial_rating,
            rd=initial_rd,
            volatility=initial_volatility,
            last_updated=datetime.now()
        )
    
    def update_rating(self, player_rating: GlickoRating, 
                     opponent_ratings: List[GlickoRating],
                     results: List[float]) -> GlickoRating:
        """Update player rating based on game results
        
        Args:
            player_rating: Current player rating
            opponent_ratings: List of opponent ratings
            results: List of results (1.0 = win, 0.5 = draw, 0.0 = loss)
        """
        if len(opponent_ratings) != len(results):
            raise ValueError("Opponent ratings and results must have same length")
        
        if not opponent_ratings:
            # No games played, only update RD for time passage
            return self._update_rd_for_time(player_rating)
        
        # Convert to Glicko-2 scale
        mu = (player_rating.rating - 1500) / 173.7178
        phi = player_rating.rd / 173.7178
        sigma = player_rating.volatility
        
        # Convert opponents to Glicko-2 scale
        mu_j = [(r.rating - 1500) / 173.7178 for r in opponent_ratings]
        phi_j = [r.rd / 173.7178 for r in opponent_ratings]
        
        # Step 1: Calculate v (estimated variance)
        v = self._calculate_v(mu, mu_j, phi_j)
        
        # Step 2: Calculate delta (estimated improvement)
        delta = self._calculate_delta(mu, mu_j, phi_j, results, v)
        
        # Step 3: Update volatility
        new_sigma = self._update_volatility(sigma, phi, v, delta)
        
        # Step 4: Update rating deviation
        phi_star = math.sqrt(phi**2 + new_sigma**2)
        new_phi = 1 / math.sqrt(1/phi_star**2 + 1/v)
        
        # Step 5: Update rating
        new_mu = mu + new_phi**2 * sum(
            self._g(phi_j[i]) * (results[i] - self._E(mu, mu_j[i], phi_j[i]))
            for i in range(len(results))
        )
        
        # Convert back to original scale
        new_rating = new_mu * 173.7178 + 1500
        new_rd = new_phi * 173.7178
        
        return GlickoRating(
            rating=new_rating,
            rd=new_rd,
            volatility=new_sigma,
            last_updated=datetime.now(),
            games_played=player_rating.games_played + len(results)
        )
    
    def _calculate_v(self, mu: float, mu_j: List[float], phi_j: List[float]) -> float:
        """Calculate estimated variance"""
        v_inv = sum(
            self._g(phi_j[i])**2 * self._E(mu, mu_j[i], phi_j[i]) * 
            (1 - self._E(mu, mu_j[i], phi_j[i]))
            for i in range(len(mu_j))
        )
        return 1 / v_inv if v_inv > 0 else float('inf')
    
    def _calculate_delta(self, mu: float, mu_j: List[float], phi_j: List[float], 
                        results: List[float], v: float) -> float:
        """Calculate estimated improvement"""
        return v * sum(
            self._g(phi_j[i]) * (results[i] - self._E(mu, mu_j[i], phi_j[i]))
            for i in range(len(results))
        )
    
    def _update_volatility(self, sigma: float, phi: float, v: float, delta: float) -> float:
        """Update volatility using iterative algorithm"""
        a = math.log(sigma**2)
        
        def f(x):
            return (math.exp(x) * (delta**2 - phi**2 - v - math.exp(x))) / \
                   (2 * (phi**2 + v + math.exp(x))**2) - (x - a) / self.tau**2
        
        # Initial bracket
        A = a
        if delta**2 > phi**2 + v:
            B = math.log(delta**2 - phi**2 - v)
        else:
            k = 1
            while f(a - k * self.tau) < 0:
                k += 1
            B = a - k * self.tau
        
        # Illinois algorithm
        fA = f(A)
        fB = f(B)
        
        while abs(B - A) > self.epsilon:
            C = A + (A - B) * fA / (fB - fA)
            fC = f(C)
            
            if fC * fB < 0:
                A = B
                fA = fB
            else:
                fA = fA / 2
            
            B = C
            fB = fC
        
        return math.exp(A / 2)
    
    def _g(self, phi: float) -> float:
        """Glicko-2 g function"""
        return 1 / math.sqrt(1 + 3 * phi**2 / math.pi**2)
    
    def _E(self, mu: float, mu_j: float, phi_j: float) -> float:
        """Expected score function"""
        return 1 / (1 + math.exp(-self._g(phi_j) * (mu - mu_j)))
    
    def _update_rd_for_time(self, rating: GlickoRating, days_elapsed: int = 1) -> GlickoRating:
        """Update RD for time passage without games"""
        # Simplified time update - would use actual time difference
        time_factor = min(1.1, 1.0 + days_elapsed * 0.001)  # Gradual RD increase
        new_rd = min(350, rating.rd * time_factor)
        
        return GlickoRating(
            rating=rating.rating,
            rd=new_rd,
            volatility=rating.volatility,
            last_updated=datetime.now(),
            games_played=rating.games_played
        )
    
    def calculate_win_probability(self, player_rating: GlickoRating, 
                                opponent_rating: GlickoRating) -> float:
        """Calculate win probability between two players"""
        # Convert to Glicko-2 scale
        mu1 = (player_rating.rating - 1500) / 173.7178
        mu2 = (opponent_rating.rating - 1500) / 173.7178
        phi2 = opponent_rating.rd / 173.7178
        
        return self._E(mu1, mu2, phi2)
