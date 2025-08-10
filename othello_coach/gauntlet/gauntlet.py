"""Gauntlet runner for self-play matches"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .glicko import GlickoRating, GlickoCalculator
from ..engine.search import search_position, SearchLimits
from ..engine.board import Board, make_move
from ..engine.strength import get_strength_profile, StrengthProfile
from ..engine.notation import moves_to_string, format_moves_with_passes


@dataclass
class GauntletMatch:
    """Single match in a gauntlet"""
    white_profile: str
    black_profile: str
    white_rating: GlickoRating
    black_rating: GlickoRating
    result: Optional[float] = None  # 1.0 = white win, 0.5 = draw, 0.0 = black win
    moves: List[int] = None
    passes: List[int] = None # Track pass moves
    game_length: int = 0
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    seed: Optional[int] = None


class GauntletRunner:
    """Runs self-play gauntlets for rating calibration"""
    
    def __init__(self, db_path: str, engine_version: str = "1.1.0"):
        self.db_path = db_path
        self.engine_version = engine_version
        self.glicko = GlickoCalculator(tau=0.5)
        
        # Performance optimizations
        self._engine_cache = {}  # Cache engine instances
        self._strength_cache = {}  # Cache strength profiles
        
        # Load or create ratings ladder
        self.ladder = self._load_ladder()
    
    def _load_ladder(self) -> Dict[str, GlickoRating]:
        """Load current ladder from database"""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        Session = sessionmaker(bind=engine)
        
        # Ensure schema exists for in-memory databases (used in tests)
        if self.db_path == ":memory:":
            self._ensure_schema(engine)
        
        ladder = {}
        with Session() as session:
            query = text("""
                SELECT profile, rating, RD, last_rated_at 
                FROM ladders 
                WHERE engine_ver = :engine_ver
            """)
            results = session.execute(query, {'engine_ver': self.engine_version}).fetchall()
            
            for row in results:
                ladder[row.profile] = GlickoRating(
                    rating=row.rating,
                    rd=row.RD,
                    volatility=0.06,  # Default
                    last_updated=row.last_rated_at
                )
        
        # Add default profiles if not present
        default_profiles = ['elo_400', 'elo_800', 'elo_1400', 'elo_2000', 'elo_2300', 'max']
        for profile in default_profiles:
            if profile not in ladder:
                ladder[profile] = self.glicko.create_initial_rating()
        
        return ladder
    
    def _ensure_schema(self, engine):
        """Ensure database schema exists (for tests)"""
        from ..db.schema_sql_loader import get_schema_sql
        # Use raw connection to execute multiple statements
        raw_conn = engine.raw_connection()
        try:
            raw_conn.executescript(get_schema_sql())
        finally:
            raw_conn.close()
    
    def run_round_robin(self, profiles: List[str], games_per_pair: int = 1000, 
                       workers: int = 4, root_noise: bool = True, 
                       progress_callback=None) -> List[GauntletMatch]:
        """Run round-robin gauntlet between profiles"""
        matches = []
        
        # Generate all pairings
        for i, white_profile in enumerate(profiles):
            for j, black_profile in enumerate(profiles):
                if i != j:  # No self-play for now
                    for game_num in range(games_per_pair):
                        match = GauntletMatch(
                            white_profile=white_profile,
                            black_profile=black_profile,
                            white_rating=self.ladder[white_profile],
                            black_rating=self.ladder[black_profile],
                            seed=random.randint(0, 2**31-1)
                        )
                        matches.append(match)
        
        # Shuffle for better parallelization
        random.shuffle(matches)
        
        import logging
        logging.getLogger(__name__).info("Running %s gauntlet matches with %s workers...", len(matches), workers)
        
        if progress_callback:
            progress_callback(f"Starting gauntlet with {len(matches)} matches...", 0)
        
        # Run matches in parallel
        completed_matches = []
        total_matches = len(matches)
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_match = {
                executor.submit(self._play_match, match, root_noise): match 
                for match in matches
            }
            
            for future in as_completed(future_to_match):
                match = future_to_match[future]
                try:
                    completed_match = future.result()
                    completed_matches.append(completed_match)
                    
                    # More frequent progress updates
                    progress_pct = (len(completed_matches) / total_matches) * 100
                    
                    # Update every 10 matches for CLI, every match for GUI
                    if len(completed_matches) % 10 == 0 or progress_callback:
                        import logging
                        logging.getLogger(__name__).info("Completed %s/%s matches (%.1f%%)", 
                                                       len(completed_matches), total_matches, progress_pct)
                        
                        if progress_callback:
                            # Provide detailed progress info
                            current_match = completed_matches[-1]
                            result_str = "W" if current_match.result == 1.0 else "B" if current_match.result == 0.0 else "D"
                            progress_callback(
                                f"Match {len(completed_matches)}/{total_matches}: "
                                f"{current_match.white_profile} vs {current_match.black_profile} = {result_str} "
                                f"({current_match.game_length} moves)",
                                progress_pct
                            )
                        
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).exception("Match failed: %s", e)
                    
                    if progress_callback:
                        progress_callback(f"Match failed: {e}", -1)
        
        if progress_callback:
            progress_callback("Updating ratings...", 95)
        
        # Update ratings
        self._update_ratings(completed_matches)
        
        if progress_callback:
            progress_callback("Gauntlet complete!", 100)
        
        return completed_matches
    
    def _get_cached_strength(self, profile: str) -> 'StrengthProfile':
        """Get cached strength profile to avoid repeated lookups"""
        if profile not in self._strength_cache:
            from ..engine.strength import get_strength_profile
            self._strength_cache[profile] = get_strength_profile(profile)
        return self._strength_cache[profile]
    
    def _play_match(self, match: GauntletMatch, root_noise: bool = True) -> GauntletMatch:
        """Play a single match"""
        match.started_at = datetime.now()
        
        # Set random seed for reproducibility
        if match.seed:
            random.seed(match.seed)
        
        # Get strength profiles
        white_strength = self._get_cached_strength(match.white_profile)
        black_strength = self._get_cached_strength(match.black_profile)
        
        # Play the game
        board = Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=0)
        moves = []
        passes = []  # Track pass moves
        
        # Track game progress for debugging
        game_start_time = time.time()
        
        while True:
            # Check for game end
            from ..engine.movegen_fast import generate_legal_mask
            legal_mask = generate_legal_mask(board.B, board.W, board.stm)
            
            if legal_mask == 0:
                # No legal moves - pass or game over
                opposite_legal = generate_legal_mask(board.B, board.W, 1 - board.stm)
                if opposite_legal == 0:
                    break  # Game over
                else:
                    # Pass - record this as a pass move
                    passes.append(len(moves))
                    board = Board(board.B, board.W, 1 - board.stm, board.ply + 1, board.hash)
                    continue
            
            # Get strength profile for current player
            strength = white_strength if board.stm == 1 else black_strength
            
            # Apply root noise for first 6 moves if enabled
            apply_noise = root_noise and len(moves) < 6
            
            # Search for best move
            move_start_time = time.time()
            move = self._get_engine_move(board, strength, apply_noise)
            move_time = time.time() - move_start_time
            
            # Log slow moves for debugging
            if move_time > 1.0:  # More than 1 second
                import logging
                logging.getLogger(__name__).warning(
                    "Slow move: %.2fs for move %d in %s vs %s game", 
                    move_time, len(moves), match.white_profile, match.black_profile
                )
            
            if move is None:
                # Log why the engine failed
                import logging
                logging.getLogger(__name__).error(
                    "Engine returned None for move in %s vs %s game at move %d. Board state: B=%s, W=%s, stm=%d, legal_moves=%s",
                    match.white_profile, match.black_profile, len(moves), 
                    bin(board.B), bin(board.W), board.stm,
                    bin(generate_legal_mask(board.B, board.W, board.stm))
                )
                break  # Engine failed
            
            # Make the move
            try:
                board, _ = make_move(board, move)
                moves.append(move)
            except:
                break  # Invalid move
            
            # Prevent infinite games
            if len(moves) > 100:
                break
        
        # Determine result
        white_discs = bin(board.W).count('1')
        black_discs = bin(board.B).count('1')
        
        if white_discs > black_discs:
            result = 1.0  # White wins
        elif black_discs > white_discs:
            result = 0.0  # Black wins
        else:
            result = 0.5  # Draw
        
        match.result = result
        match.moves = moves
        match.passes = passes  # Store pass information
        match.game_length = len(moves) + len(passes)
        match.finished_at = datetime.now()
        
        return match
    
    def _get_engine_move(self, board: Board, strength: StrengthProfile, apply_noise: bool = False) -> Optional[int]:
        """Get move from engine with given strength"""
        try:
            # Search with strength parameters
            limits = SearchLimits(
                max_depth=strength.depth,
                time_ms=strength.soft_time_ms
            )
            result = search_position(board, limits)
            
            if not result or not result.pv:
                # Log why search failed
                import logging
                logging.getLogger(__name__).error(
                    "Search failed for %s vs %s: result=%s, pv=%s",
                    "white" if board.stm == 1 else "black",
                    "black" if board.stm == 1 else "white",
                    result, result.pv if result else None
                )
                return None
            
            # Apply strength-based move selection
            if strength.noise_temp > 0 or apply_noise:
                return self._apply_strength_selection(board, result, strength, apply_noise)
            else:
                return result.pv[0]
                
        except Exception:
            return None
    
    def _apply_strength_selection(self, board: Board, result, strength: StrengthProfile, apply_noise: bool) -> int:
        """Apply strength-based move selection with noise"""
        # Get legal moves and their scores
        from ..engine.movegen_fast import generate_legal_mask
        legal_mask = generate_legal_mask(board.B, board.W, board.stm)
        
        legal_moves = []
        for sq in range(64):
            if legal_mask & (1 << sq):
                legal_moves.append(sq)
        
        # This should never happen if called correctly, but provide a fallback
        if not legal_moves:
            # If somehow no legal moves, this indicates a bug - log and return a safe move
            import logging
            logging.getLogger(__name__).error(
                "No legal moves found in _apply_strength_selection - this should not happen"
            )
            # Return a default move (this should never be reached in normal play)
            return 0
        
        # For simplicity, use best move with some noise
        best_move = result.pv[0] if result.pv else legal_moves[0]
        
        # Apply blunder probability
        blunder_prob = strength.blunder_prob
        if random.random() < blunder_prob:
            # Pick a suboptimal move
            other_moves = [m for m in legal_moves if m != best_move]
            if other_moves:
                return random.choice(other_moves)
        
        # Apply top-k selection
        top_k = strength.top_k
        if top_k > 1 and len(legal_moves) > 1:
            # For simplicity, randomly pick from top-k legal moves
            available_moves = legal_moves[:min(top_k, len(legal_moves))]
            return random.choice(available_moves)
        
        return best_move
    
    def _update_ratings(self, matches: List[GauntletMatch]):
        """Update Glicko-2 ratings based on match results"""
        # Group matches by player
        player_results = {}
        
        # Batch save all games at once instead of one by one
        # Use a separate thread for database operations to avoid blocking
        import threading
        db_thread = threading.Thread(target=self._batch_save_games, args=(matches,))
        db_thread.start()
        
        for match in matches:
            if match.result is None:
                continue
            
            # White player results
            if match.white_profile not in player_results:
                player_results[match.white_profile] = {'opponents': [], 'results': []}
            player_results[match.white_profile]['opponents'].append(self.ladder[match.black_profile])
            player_results[match.white_profile]['results'].append(match.result)
            
            # Black player results  
            if match.black_profile not in player_results:
                player_results[match.black_profile] = {'opponents': [], 'results': []}
            player_results[match.black_profile]['opponents'].append(self.ladder[match.white_profile])
            player_results[match.black_profile]['results'].append(1.0 - match.result)
        
        # Update each player's rating
        for profile, data in player_results.items():
            old_rating = self.ladder[profile]
            new_rating = self.glicko.update_rating(
                old_rating,
                data['opponents'],
                data['results']
            )
            self.ladder[profile] = new_rating
            
            import logging
            logging.getLogger(__name__).info(
                "%s: %.0f±%.0f → %.0f±%.0f",
                profile, old_rating.rating, old_rating.rd, new_rating.rating, new_rating.rd,
            )
        
        # Wait for database save to complete
        db_thread.join()
        
        # Save to database
        self._save_ladder()
    
    def _batch_save_games(self, matches: List[GauntletMatch]):
        """Batch save all games to database efficiently"""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        if not matches:
            return
            
        engine = create_engine(f"sqlite:///{self.db_path}")
        
        # Ensure schema exists for in-memory databases
        if self.db_path == ":memory:":
            self._ensure_schema(engine)
            
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # Prepare batch insert
            games_data = []
            for match in matches:
                if match.result is None:
                    continue
                    
                # Convert moves list to coordinate notation string with passes
                moves_str = format_moves_with_passes(match.moves, getattr(match, 'passes', []))
                
                # Create tags for the game
                tags = f"gauntlet,{match.white_profile}_vs_{match.black_profile}"
                
                games_data.append({
                    'start_hash': "0000000810000000_0000001008000000_0_0",  # Standard starting position
                    'result': match.result,
                    'length': match.game_length,
                    'tags': tags,
                    'moves': moves_str,
                    'started_at': match.started_at,
                    'finished_at': match.finished_at
                })
            
            if games_data:
                # Batch insert all games
                query = text("""
                    INSERT INTO games(start_hash, result, length, tags, moves, started_at, finished_at)
                    VALUES (:start_hash, :result, :length, :tags, :moves, :started_at, :finished_at)
                """)
                session.execute(query, games_data)
                session.commit()
    
    def _save_ladder(self):
        """Save updated ladder to database"""
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        engine = create_engine(f"sqlite:///{self.db_path}")
        
        # Ensure schema exists for in-memory databases
        if self.db_path == ":memory:":
            self._ensure_schema(engine)
            
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            for profile, rating in self.ladder.items():
                # Upsert rating
                query = text("""
                    INSERT OR REPLACE INTO ladders 
                    (engine_ver, profile, rating, RD, last_rated_at)
                    VALUES (:engine_ver, :profile, :rating, :rd, :timestamp)
                """)
                session.execute(query, {
                    'engine_ver': self.engine_version,
                    'profile': profile,
                    'rating': rating.rating,
                    'rd': rating.rd,
                    'timestamp': rating.last_updated
                })
            session.commit()
    

    
    def get_ladder_standings(self) -> List[Tuple[str, GlickoRating]]:
        """Get current ladder standings"""
        standings = sorted(
            self.ladder.items(),
            key=lambda x: x[1].rating,
            reverse=True
        )
        return standings
