from __future__ import annotations

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt6.QtGui import QBrush, QColor, QPen
from PyQt6.QtCore import QRectF, Qt, QPointF, QElapsedTimer, QTimer, pyqtSignal

from ..engine.board import start_board, legal_moves_mask, make_move, compute_hash, Board
from ..engine.search import Searcher, SearchLimits, SearchResult
from ..engine.solver import get_solver_threshold
from ..engine.strength import get_strength_profile, PROFILES
from ..insights.overlays import mobility_heat as ov_mobility_heat
from ..insights.overlays import stability_heat as ov_stability_heat
from ..insights.overlays import parity_map as ov_parity_map
from ..insights.overlays import corner_tension as ov_corner_tension
from ..tools.diag import log_event


class BoardWidget(QGraphicsView):
    # Signal emitted when game state changes (for UI updates)
    game_state_changed = pyqtSignal(dict)
    
    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setMinimumSize(300, 300)
        self.board = start_board()
        self.game_over = False
        self.overlay_flags = {"mobility": False, "parity": False, "stability": False, "corner": False}
        self.last_move_sq: int | None = None  # index 0..63 of most recent move (previous player)
        
        # Game mode settings
        self.game_mode = "human_vs_human"  # "human_vs_human", "human_vs_cpu", "cpu_vs_cpu"
        self.cpu_black_strength = "elo_1400"
        self.cpu_white_strength = "elo_1400"
        self.cpu_move_delay_ms = 1000
        
        # Game state tracking
        self.last_move_info = ""  # Track information about the last move/action
        
        # CPU player components
        self.searcher = Searcher()
        self.cpu_timer = QTimer()
        self.cpu_timer.setSingleShot(True)
        self.cpu_timer.timeout.connect(self._make_cpu_move)
        self.cpu_busy = False
        # Watchdog to recover from any missed timers or stalls
        self.cpu_watchdog = QTimer()
        self.cpu_watchdog.setInterval(750)
        self.cpu_watchdog.timeout.connect(self._cpu_watchdog_tick)
        self.cpu_watchdog.start()
        self._stall_ticks = 0
        self._last_ply_seen = self.board.ply
        
        self._ensure_playable_state()
        self._draw()
        self._emit_game_state()

    def _draw(self) -> None:
        s = self.scene()
        assert s is not None
        s.clear()
        size = 8
        square = 40.0
        board_px = square * size
        s.setSceneRect(QRectF(0, 0, board_px, board_px))
        dark_green = QColor(20, 110, 50)
        light_green = QColor(30, 140, 70)
        # Draw squares
        for r in range(size):
            for c in range(size):
                rect = QRectF(c * square, r * square, square, square)
                color = dark_green if (r + c) % 2 == 0 else light_green
                s.addRect(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
        # Draw discs
        B = self.board.B
        W = self.board.W
        for i in range(64):
            bit = 1 << i
            if not (B & bit or W & bit):
                continue
            r, c = divmod(i, 8)
            rect = QRectF(c * square + 4, r * square + 4, square - 8, square - 8)
            color = QColor("black") if (B & bit) else QColor("white")
            s.addEllipse(rect, QPen(Qt.GlobalColor.black), QBrush(color))

        # Highlight last move by previous player prominently
        if self.last_move_sq is not None:
            r, c = divmod(self.last_move_sq, 8)
            # Outer ring
            ring_pen = QPen(QColor(255, 215, 0))  # gold
            ring_pen.setWidth(4)
            s.addRect(QRectF(c * square + 2, r * square + 2, square - 4, square - 4), ring_pen)
            # Inner dot
            dot_color = QColor(255, 215, 0, 180)
            s.addEllipse(QRectF(c * square + square/2 - 6, r * square + square/2 - 6, 12, 12), QPen(Qt.PenStyle.NoPen), QBrush(dot_color))
        # Legal move pips for current player
        legal = legal_moves_mask(self.board)
        pen = QPen(QColor(255, 255, 0))
        pen.setWidth(2)
        for i in range(64):
            if legal & (1 << i):
                r, c = divmod(i, 8)
                rect = QRectF(c * square + square / 2 - 4, r * square + square / 2 - 4, 8, 8)
                s.addEllipse(rect, pen)

        # Overlays
        try:
            if self.overlay_flags.get("mobility"):
                t0 = QElapsedTimer()
                t0.start()
                heat = ov_mobility_heat(self.board)
                # Normalize alpha across values for clearer contrast
                if heat:
                    vmin = min(heat.values())
                    vmax = max(heat.values())
                    span = max(1, vmax - vmin)
                else:
                    vmin = 0; span = 1
                for sq, val in heat.items():
                    r, c = divmod(sq, 8)
                    alpha = 50 + int(((val - vmin) / span) * 180)
                    color = QColor(0, 200, 255, alpha)
                    rect = QRectF(c * square + 10, r * square + 10, square - 20, square - 20)
                    s.addEllipse(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
                log_event("ui.board", "overlay_mobility", ms=int(t0.elapsed()))
            if self.overlay_flags.get("stability"):
                t0 = QElapsedTimer(); t0.start()
                heat = ov_stability_heat(self.board)
                if heat:
                    vmin = min(heat.values())
                    vmax = max(heat.values())
                    span = max(1, vmax - vmin)
                else:
                    vmin = 0; span = 1
                for sq, val in heat.items():
                    r, c = divmod(sq, 8)
                    alpha = 50 + int(((val - vmin) / span) * 180)
                    color = QColor(255, 140, 0, alpha)
                    rect = QRectF(c * square + 12, r * square + 12, square - 24, square - 24)
                    s.addEllipse(rect, QPen(Qt.PenStyle.NoPen), QBrush(color))
                log_event("ui.board", "overlay_stability", ms=int(t0.elapsed()))
            if self.overlay_flags.get("parity"):
                t0 = QElapsedTimer(); t0.start()
                pm = ov_parity_map(self.board)
                for sq in pm.get("odd", []):
                    r, c = divmod(sq, 8)
                    rect = QRectF(c * square + 2, r * square + 2, square - 4, square - 4)
                    s.addRect(rect, QPen(QColor(200, 0, 200)))
                for sq in pm.get("even", []):
                    r, c = divmod(sq, 8)
                    rect = QRectF(c * square + 4, r * square + 4, square - 8, square - 8)
                    s.addRect(rect, QPen(QColor(0, 200, 0)))
                for sq in pm.get("must_move_border", []):
                    r, c = divmod(sq, 8)
                    rect = QRectF(c * square + 6, r * square + 6, square - 12, square - 12)
                    s.addRect(rect, QPen(QColor(255, 0, 0)))
                log_event("ui.board", "overlay_parity", ms=int(t0.elapsed()))
            if self.overlay_flags.get("corner"):
                t0 = QElapsedTimer(); t0.start()
                arrows = ov_corner_tension(self.board)
                for frm, corner, kind in arrows:
                    r1, c1 = divmod(frm, 8)
                    r2, c2 = divmod(corner, 8)
                    pen = QPen(QColor(0, 180, 0) if kind == "secures" else QColor(180, 0, 0))
                    pen.setWidth(2)
                    s.addLine(c1 * square + square/2, r1 * square + square/2, c2 * square + square/2, r2 * square + square/2, pen)
                log_event("ui.board", "overlay_corner", ms=int(t0.elapsed()))
        except Exception as e:
            # overlays are best-effort; never break board drawing
            # Uncomment for debugging: print(f"Warning: Overlay rendering failed: {e}")
            pass

    def _ensure_playable_state(self, schedule: bool = True) -> None:
        """Pass turn automatically if current side has no legal moves.
        If both sides have no legal moves, mark game over.
        """
        # Try at most twice to avoid infinite loops
        for _ in range(2):
            if legal_moves_mask(self.board) != 0:
                # Current player has legal moves
                if schedule:
                    self._schedule_cpu_move_if_needed()
                return
            
            # No legal moves for current side → try passing
            next_stm = 1 - self.board.stm
            # Check if opponent has moves
            temp = Board(self.board.B, self.board.W, next_stm, self.board.ply, compute_hash(self.board.B, self.board.W, next_stm))
            if legal_moves_mask(temp) == 0:
                # Game over: neither side can move
                self.game_over = True
                self._emit_game_state()
                return
            
            # Apply pass: toggle stm and increment ply, recompute hash
            self.board = Board(self.board.B, self.board.W, next_stm, self.board.ply + 1, compute_hash(self.board.B, self.board.W, next_stm))
            
            # Log the pass
            player_name = "Black" if (1 - next_stm) == 0 else "White"
            log_event("game.pass", "auto", player=player_name, ply=self.board.ply - 1)
            print(f"{player_name} passes (no legal moves)")
            
            # Track pass information for UI
            self.last_move_info = f"{player_name} passed"
            
            self._emit_game_state()
            
            # After applying the pass, continue the loop to check if the new current player
            # (who now has legal moves) needs to move automatically (CPU)
        
        # If we exit the loop, check one more time for CPU moves
        if schedule:
            self._schedule_cpu_move_if_needed()

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        # If current side has no moves, auto-pass first
        # Do not schedule within the CPU move; we will schedule in finally
        self._ensure_playable_state(schedule=False)
        if self.game_over:
            return
        
        # Only allow human moves
        if not self._is_human_turn():
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            pos: QPointF = self.mapToScene(event.position().toPoint())  # type: ignore[attr-defined]
            square = 40.0
            c = int(pos.x() // square)
            r = int(pos.y() // square)
            if 0 <= r < 8 and 0 <= c < 8:
                idx = r * 8 + c
                legal = legal_moves_mask(self.board)
                if legal & (1 << idx):
                    self.board, _ = make_move(self.board, idx)
                    self.last_move_sq = idx
                    log_event("game.move", "human", square=idx, stm=1-self.board.stm)
                    
                    # Track move information for UI
                    player_name = "Black" if (1 - self.board.stm) == 0 else "White"
                    self.last_move_info = f"{player_name} played"
                    
                    # After a move, opponent might have to pass or CPU might need to move
                    self._ensure_playable_state()
                    self._draw()
                    self._emit_game_state()
                    return
        super().mousePressEvent(event)

    def apply_overlays(self, flags: dict) -> None:
        self.overlay_flags.update(flags)
        self._draw()
    
    def set_game_mode(self, mode: str) -> None:
        """Set the game mode: 'human_vs_human', 'human_vs_cpu', or 'cpu_vs_cpu'"""
        self.game_mode = mode
        self.cpu_timer.stop()  # Stop any pending CPU moves
        self._ensure_playable_state()
        self._emit_game_state()
    
    def set_cpu_strength(self, black_strength: str = None, white_strength: str = None) -> None:
        """Set CPU strength profiles for black and/or white"""
        if black_strength and black_strength in PROFILES:
            self.cpu_black_strength = black_strength
        if white_strength and white_strength in PROFILES:
            self.cpu_white_strength = white_strength
        self._emit_game_state()
    
    def set_cpu_move_delay(self, delay_ms: int) -> None:
        """Set delay for CPU moves to make them feel more natural"""
        self.cpu_move_delay_ms = max(0, min(5000, delay_ms))
    
    def _is_human_turn(self) -> bool:
        """Check if it's a human player's turn"""
        if self.game_over:
            return False
        if self.game_mode == "human_vs_human":
            return True
        elif self.game_mode == "human_vs_cpu":
            return self.board.stm == 0  # Human plays black (0)
        elif self.game_mode == "cpu_vs_cpu":
            return False
        return True
    
    def _is_cpu_turn(self) -> bool:
        """Check if it's a CPU player's turn"""
        if self.game_over:
            return False
        if self.game_mode == "human_vs_human":
            return False
        elif self.game_mode == "human_vs_cpu":
            return self.board.stm == 1  # CPU plays white (1)
        elif self.game_mode == "cpu_vs_cpu":
            return True
        return False
    
    def _schedule_cpu_move_if_needed(self) -> None:
        """Schedule a CPU move if it's CPU's turn"""
        if not self._is_cpu_turn() or self.game_over or self.cpu_busy:
            return
        # Immediate scheduling if delay is zero
        if self.cpu_move_delay_ms <= 0:
            log_event("game.cpu", "schedule_immediate", ply=self.board.ply, delay_ms=self.cpu_move_delay_ms)
            QTimer.singleShot(0, self._make_cpu_move)
            return
        if not self.cpu_timer.isActive():
            log_event("game.cpu", "schedule_timer", ply=self.board.ply, delay_ms=self.cpu_move_delay_ms)
            self.cpu_timer.start(self.cpu_move_delay_ms)

    def _cpu_watchdog_tick(self) -> None:
        """Watchdog to ensure CPU keeps moving when it should."""
        try:
            if self.game_over:
                self._stall_ticks = 0
                return
            # Progress tracking
            if self.board.ply != self._last_ply_seen:
                self._stall_ticks = 0
                self._last_ply_seen = self.board.ply
            # If CPU should move but nothing is scheduled, try to kick it
            if self._is_cpu_turn() and not self.cpu_busy and not self.cpu_timer.isActive():
                self._stall_ticks += 1
                if self.cpu_move_delay_ms <= 0:
                    log_event("game.cpu", "watchdog_kick_immediate", ply=self.board.ply, stall_ticks=self._stall_ticks)
                    QTimer.singleShot(0, self._make_cpu_move)
                else:
                    log_event("game.cpu", "watchdog_kick_timer", ply=self.board.ply, stall_ticks=self._stall_ticks, delay_ms=self.cpu_move_delay_ms)
                    self.cpu_timer.start(self.cpu_move_delay_ms)
                # If repeatedly stalled, force a fallback move to guarantee progress
                if self._stall_ticks >= 3:
                    if legal_moves_mask(self.board) != 0:
                        log_event("game.cpu", "watchdog_fallback", ply=self.board.ply)
                        self._play_fallback_move()
                        self._stall_ticks = 0
        except Exception:
            # Never let watchdog crash the UI
            pass
    
    def _make_cpu_move(self) -> None:
        """Make a CPU move using the search engine"""
        if self.game_over or not self._is_cpu_turn():
            return

        # First check if we need to handle passes before attempting to search
        self._ensure_playable_state(schedule=False)

        # After ensuring playable state, check again if it's still CPU's turn
        if self.game_over or not self._is_cpu_turn():
            return

        self.cpu_busy = True
        try:
            empties = 64 - (self.board.B | self.board.W).bit_count()
            log_event("game.cpu", "search_start", ply=self.board.ply, stm=self.board.stm, empties=empties)
            # Get strength profile for current player
            strength_name = self.cpu_black_strength if self.board.stm == 0 else self.cpu_white_strength
            profile = get_strength_profile(strength_name)
            
            # Set up search limits based on strength profile
            endgame_threshold = get_solver_threshold()
            limits = SearchLimits(
                max_depth=profile.depth,
                time_ms=profile.soft_time_ms,
                node_cap=500_000,  # Reasonable limit for GUI responsiveness
                endgame_exact_empties=endgame_threshold
            )
            
            # Reset per-search counters to avoid hitting node cap across moves
            try:
                self.searcher.nodes = 0
            except Exception:
                pass
            # Search for best move
            result = self.searcher.search(self.board, limits)
            
            if result.best_move is not None:
                # Apply some randomness/blunders based on strength profile
                final_move = self._apply_strength_effects(result.best_move, profile)
                
                # Make the move
                self.board, _ = make_move(self.board, final_move)
                self.last_move_sq = final_move
                log_event(
                    "game.move",
                    "cpu",
                    square=final_move,
                    stm=1 - self.board.stm,
                    strength=strength_name,
                    depth=result.depth,
                    nodes=result.nodes,
                    time_ms=result.time_ms,
                    score_cp=result.score_cp,
                )
                
                # Track move information for UI  
                player_name = "Black" if (1 - self.board.stm) == 0 else "White"
                self.last_move_info = f"{player_name} played (CPU)"
                
                # Update game state after move
                self._ensure_playable_state(schedule=False)
                self._draw()
                self._emit_game_state()
            else:
                # Failsafe: if search produced no move, pick a legal move if any
                if legal_moves_mask(self.board) != 0:
                    log_event("game.cpu", "search_no_move_fallback", ply=self.board.ply)
                    self._play_fallback_move()
                else:
                    # No legal moves indeed; emit and reschedule after pass handling
                    log_event("game.error", "cpu_no_moves", stm=self.board.stm)
                    # Attempt to reschedule to avoid stalling
                    self._schedule_cpu_move_if_needed()
        
        except Exception as e:
            log_event("game.error", "cpu_move_failed", error=str(e))
            print(f"CPU move failed: {e}")
            # Attempt to recover by rescheduling
            self._schedule_cpu_move_if_needed()
        finally:
            self.cpu_busy = False
            # After finishing, ensure next move is queued if still CPU turn
            self._schedule_cpu_move_if_needed()
    
    def _apply_strength_effects(self, best_move: int, profile) -> int:
        """Apply strength-based effects like blunders and randomness"""
        import random
        
        # Check for blunder
        if random.random() < profile.blunder_prob:
            # Make a random legal move instead
            legal = legal_moves_mask(self.board)
            legal_moves = []
            m = legal
            while m:
                lsb = m & -m
                legal_moves.append(lsb.bit_length() - 1)
                m ^= lsb
            if legal_moves:
                return random.choice(legal_moves)
        
        # Apply top-k randomization
        if profile.top_k > 1:
            # For simplicity, just add some randomness to move selection
            # In a full implementation, we'd evaluate top moves and pick randomly
            if random.random() < 0.3:  # 30% chance of not playing best move
                legal = legal_moves_mask(self.board)
                legal_moves = []
                m = legal
                while m:
                    lsb = m & -m
                    legal_moves.append(lsb.bit_length() - 1)
                    m ^= lsb
                if len(legal_moves) > 1:
                    # Remove best move and pick randomly from others
                    legal_moves = [m for m in legal_moves if m != best_move]
                    if legal_moves:
                        return random.choice(legal_moves)
        
        return best_move
    
    def _emit_game_state(self) -> None:
        """Emit current game state for UI updates"""
        black_count = self.board.B.bit_count()
        white_count = self.board.W.bit_count()
        
        state = {
            "to_move": "Black" if self.board.stm == 0 else "White",
            "black_count": black_count,
            "white_count": white_count,
            "ply": self.board.ply,
            "game_over": self.game_over,
            "game_mode": self.game_mode,
            "cpu_thinking": self.cpu_busy or self.cpu_timer.isActive(),
            "is_human_turn": self._is_human_turn(),
            "last_move_info": self.last_move_info,
            "winner": None
        }
        
        if self.game_over:
            if black_count > white_count:
                state["winner"] = "Black"
            elif white_count > black_count:
                state["winner"] = "White"
            else:
                state["winner"] = "Draw"
        
        self.game_state_changed.emit(state)

    def _play_fallback_move(self) -> None:
        """Play a deterministic legal move as a last-resort failsafe."""
        legal = legal_moves_mask(self.board)
        if legal == 0:
            return
        lsb = legal & -legal
        fallback_move = lsb.bit_length() - 1
        self.board, _ = make_move(self.board, fallback_move)
        self.last_move_sq = fallback_move
        log_event("game.move", "cpu_fallback", square=fallback_move, stm=1-self.board.stm)
        self._ensure_playable_state()
        self._draw()
        self._emit_game_state()
    
    def new_game(self) -> None:
        """Start a new game"""
        self.cpu_timer.stop()
        self.board = start_board()
        self.game_over = False
        self.last_move_info = "New game started"
        self._ensure_playable_state()
        self._draw()
        self._emit_game_state()
