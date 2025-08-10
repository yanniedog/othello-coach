from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
import math
import sqlite3
from typing import List, Tuple, Optional
from pathlib import Path

from ..engine.board import Board
from ..engine.eval import evaluate_position
from ..gauntlet.calibration import CalibrationManager
from ..db.queries import get_position


class AdvantageGraphWidget(QWidget):
    """Real-time graph showing comparative advantage between players"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Set minimum size with 16:9 aspect ratio
        self.setMinimumSize(320, 180)  # 16:9 ratio
        # Allow the widget to expand while maintaining aspect ratio
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Set background color for the graph area
        self.setStyleSheet("QWidget { background-color: #1e1e1e; }")
        
        # Data storage
        self.advantage_history: List[Tuple[int, int]] = []  # (move_number, advantage_score)
        self.max_moves = 60  # Maximum moves to display (typical Othello game)
        self.current_move = 0
        
        # Graph appearance
        self.grid_color = QColor(100, 100, 100, 80)
        self.axis_color = QColor(200, 200, 200)
        self.line_color = QColor(0, 150, 255)
        self.zero_line_color = QColor(255, 255, 255, 120)
        self.background_color = QColor(30, 30, 30)
        
        # Initialize calibration manager for win probability
        self.calibration_manager = None
        self._init_calibration()
        
        # Labels
        self.setup_labels()
        
        # Update timer for smooth animations
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)  # 20 FPS
        self.update_timer.timeout.connect(self.update)
        
    def _init_calibration(self):
        """Initialize the calibration manager for win probability"""
        try:
            # Try to find the database path
            db_path = self._find_database_path()
            if db_path and db_path.exists():
                self.calibration_manager = CalibrationManager(str(db_path), "1.1.0")
                # Try to load existing calibration data
                self._load_calibration_data()
            else:
                # Create a default calibration if no database exists
                self._create_default_calibration()
        except Exception as e:
            # Fallback to default calibration if anything fails
            self._create_default_calibration()
    
    def _find_database_path(self) -> Optional[Path]:
        """Find the database path from common locations"""
        possible_paths = [
            Path("othello_coach.db"),
            Path("data/othello_coach.db"),
            Path.home() / ".othello_coach" / "othello_coach.db",
            Path(__file__).parent.parent.parent / "othello_coach.db"
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
    
    def _load_calibration_data(self):
        """Load calibration data from database"""
        if not self.calibration_manager:
            return
            
        try:
            # Try to get win probability calibration
            if hasattr(self.calibration_manager, 'win_prob_calibration') and self.calibration_manager.win_prob_calibration:
                # Calibration data exists
                pass
            else:
                # No calibration data, try to create from historical games
                self._calibrate_from_historical_games()
        except Exception:
            # Fallback to default calibration
            self._create_default_calibration()
    
    def _calibrate_from_historical_games(self):
        """Calibrate win probability from historical games in the database"""
        if not self.calibration_manager:
            return
            
        try:
            db_path = self._find_database_path()
            if not db_path:
                return
                
            # Connect to database and get historical game data
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get games with their results and try to find corresponding analyses
            cursor.execute("""
                SELECT g.id, g.result, g.length, g.moves, a.score, a.depth
                FROM games g
                LEFT JOIN analyses a ON g.start_hash = a.hash
                WHERE a.depth >= 8  -- Only use deep analysis
                ORDER BY g.finished_at DESC
                LIMIT 1000  -- Limit to recent games
            """)
            
            game_data = []
            for row in cursor.fetchall():
                game_id, result, length, moves, score, depth = row
                if score is not None and result is not None:
                    # Convert result to win probability (0.0 = black loss, 0.5 = draw, 1.0 = black win)
                    if result == 0:  # Black loss
                        win_prob = 0.0
                    elif result == 1:  # Black win
                        win_prob = 1.0
                    else:  # Draw
                        win_prob = 0.5
                    
                    game_data.append((score, win_prob))
            
            conn.close()
            
            # If we have enough data, calibrate the win probability
            if len(game_data) >= 50:
                self.calibration_manager.calibrate_win_probability(game_data)
                
        except Exception as e:
            # If anything fails, fall back to default calibration
            self._create_default_calibration()
    
    def _create_default_calibration(self):
        """Create a default calibration based on typical Othello evaluation patterns"""
        if not self.calibration_manager:
            return
            
        # Create synthetic calibration data based on typical Othello patterns
        # This provides reasonable defaults when no historical data is available
        synthetic_data = []
        
        # Generate data points for various evaluation scores
        for score in range(-2000, 2001, 100):
            # Use a logistic function: P(win) = 1 / (1 + exp(-(a + b * score)))
            # For Othello, a typical conversion is roughly 1000 cp = 80% win probability
            if score > 0:
                # Black advantage
                win_prob = 0.5 + (0.4 * score / 1000.0)
                win_prob = max(0.01, min(0.99, win_prob))
            else:
                # White advantage
                win_prob = 0.5 - (0.4 * abs(score) / 1000.0)
                win_prob = max(0.01, min(0.99, win_prob))
            
            synthetic_data.append((float(score), win_prob))
        
        # Calibrate using synthetic data
        try:
            self.calibration_manager.calibrate_win_probability(synthetic_data)
        except Exception:
            # If calibration fails, we'll use the synthetic data directly
            pass
        
    def setup_labels(self):
        """Setup the widget layout with labels"""
        layout = QVBoxLayout(self)
        # Reduce margins to give more space to the graph
        layout.setContentsMargins(3, 3, 3, 3)
        
        # Title - make it more compact
        title_label = QLabel("Predicted Final Score")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(9)  # Reduced font size
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; margin-bottom: 2px; background-color: transparent;")  # Added transparent background
        layout.addWidget(title_label)
        
        # Minimal spacing before the graph area
        layout.addSpacing(2)
        
        # Current advantage display - make it more compact
        self.advantage_label = QLabel("Predicted: Even (32-32)")
        self.advantage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.advantage_label.setStyleSheet("color: white; font-size: 8px; margin-top: 2px; background-color: transparent;")  # Added transparent background
        layout.addWidget(self.advantage_label)
        
        # Add stretch to push everything to the top and give maximum space to the graph
        layout.addStretch()
        
    def update_advantage(self, board: Board):
        """Update the advantage graph with current board position"""
        # Calculate advantage (positive = Black advantage, negative = White advantage)
        # This evaluates the overall board position, not just the last move
        advantage = evaluate_position(board)
        
        # Only increment move counter if this is a new position (ply increased)
        # The board.ply represents the actual move number in the game
        if not self.advantage_history or board.ply > self.current_move:
            # This is a new move - add to history
            # Handle the special case of the initial position (ply=0)
            if board.ply == 0 and not self.advantage_history:
                # Initial board position - add it as move 0
                self.advantage_history.append((0, advantage))
                self.current_move = 0
            elif board.ply > 0:
                # Regular moves - add to history
                self.advantage_history.append((board.ply, advantage))
                self.current_move = board.ply
            
            # Keep only recent history
            if len(self.advantage_history) > self.max_moves:
                self.advantage_history.pop(0)
        else:
            # This is just a state update (e.g., CPU thinking, analysis) - don't add to history
            # But we can update the current advantage display
            pass
        
        # Update advantage label with realistic final score prediction
        self._update_advantage_label(advantage)
        
        # Trigger redraw
        self.update()
        
    def update_display_only(self, board: Board):
        """Update the advantage display without adding to history (for analysis, thinking states)"""
        # Calculate advantage for display purposes
        advantage = evaluate_position(board)
        
        # Update advantage label with realistic final score prediction
        self._update_advantage_label(advantage)
        
        # Trigger redraw
        self.update()
        
    def _update_advantage_label(self, advantage: int) -> None:
        """Update the advantage label with probability-based final score prediction"""
        if not self.advantage_history:
            # No game data yet, show neutral prediction
            self.advantage_label.setText("Predicted: Even (32-32)")
            self.advantage_label.setStyleSheet("color: white; font-size: 8px; margin-top: 2px; background-color: transparent;")
            return
            
        # Calculate current piece count and remaining pieces
        current_move = self.current_move
        total_pieces_played = current_move * 2  # Each move places 2 pieces (1 per player)
        pieces_remaining = 64 - total_pieces_played
        
        # The prediction should become more accurate as the game progresses
        # Early game: more uncertainty, late game: more precise
        confidence_factor = min(1.0, total_pieces_played / 40.0)  # Full confidence after 20 moves
        
        # Detect significant immediate changes (like giving away corners)
        # If there's a major change in advantage, prioritize current state over trend
        significant_change = False
        if len(self.advantage_history) >= 2:
            last_advantage = self.advantage_history[-2][1]  # Previous move's advantage
            change_magnitude = abs(advantage - last_advantage)
            # Consider it significant if advantage changed by more than 500 points
            # This would catch major blunders like giving away corners
            if change_magnitude > 500:
                significant_change = True
        
        # Analyze the trend and trajectory of the game
        # Look at recent moves to see which direction the advantage is heading
        if len(self.advantage_history) >= 3:
            # Get the last 3 moves to analyze trend
            recent_moves = self.advantage_history[-3:]
            move_numbers = [move for move, _ in recent_moves]
            scores = [score for _, score in recent_moves]
            
            # Calculate the trend (direction and rate of change)
            if len(scores) >= 2:
                # Simple trend: positive means advantage is increasing for Black
                trend = scores[-1] - scores[0]
                trend_per_move = trend / max(1, move_numbers[-1] - move_numbers[0])
                
                # Project the trend forward to estimate final outcome
                # Consider how many moves are left and how the advantage is changing
                moves_remaining = max(0, 60 - current_move)  # Assume ~60 moves total
                
                # Project current advantage forward based on trend
                projected_advantage = advantage + (trend_per_move * moves_remaining * 0.5)  # Conservative projection
                
                # Make prediction more responsive to immediate changes by giving current advantage more weight
                # This ensures major blunders (like giving away corners) are immediately reflected
                if significant_change:
                    # For significant changes, heavily weight the current advantage
                    weighted_advantage = (advantage * 0.95) + (projected_advantage * 0.05)
                else:
                    # Normal weighting
                    weighted_advantage = (advantage * 0.85) + (projected_advantage * 0.15)
            else:
                weighted_advantage = advantage
        else:
            weighted_advantage = advantage
        
        # Use win probability calibration for accurate prediction
        if self.calibration_manager and hasattr(self.calibration_manager, 'get_win_probability'):
            try:
                # Get win probability for Black from calibration
                black_win_prob = self.calibration_manager.get_win_probability(weighted_advantage)
                
                if black_win_prob is not None:
                    # Convert probability to final score prediction
                    # This is based on historical game data rather than arbitrary scaling
                    predicted_score_diff = self._probability_to_score_difference(black_win_prob, pieces_remaining, confidence_factor)
                    
                    # Calculate predicted final scores
                    if predicted_score_diff > 0:
                        # Black advantage
                        black_score = 32 + int(predicted_score_diff)
                        white_score = 32 - int(predicted_score_diff)
                        # Ensure scores are within valid range (0-64)
                        black_score = max(0, min(64, black_score))
                        white_score = max(0, min(64, white_score))
                        
                        # Show confidence level and probability
                        if confidence_factor < 0.3:
                            confidence_text = " (Early)"
                        elif confidence_factor < 0.7:
                            confidence_text = " (Mid)"
                        else:
                            confidence_text = " (Late)"
                            
                        prob_text = f" ({black_win_prob:.1%})"
                        self.advantage_label.setText(f"Predicted: Black {black_score}-{white_score}{confidence_text}{prob_text}")
                        self.advantage_label.setStyleSheet("color: #00ff00; font-size: 8px; margin-top: 2px; background-color: transparent;")
                    elif predicted_score_diff < 0:
                        # White advantage
                        white_score = 32 + int(abs(predicted_score_diff))
                        black_score = 32 - int(abs(predicted_score_diff))
                        # Ensure scores are within valid range (0-64)
                        white_score = max(0, min(64, white_score))
                        black_score = max(0, min(64, black_score))
                        
                        # Show confidence level and probability
                        if confidence_factor < 0.3:
                            confidence_text = " (Early)"
                        elif confidence_factor < 0.7:
                            confidence_text = " (Mid)"
                        else:
                            confidence_text = " (Late)"
                            
                        white_win_prob = 1.0 - black_win_prob
                        prob_text = f" ({white_win_prob:.1%})"
                        self.advantage_label.setText(f"Predicted: White {white_score}-{black_score}{confidence_text}{prob_text}")
                        self.advantage_label.setStyleSheet("color: #ff0000; font-size: 8px; margin-top: 2px; background-color: transparent;")
                    else:
                        # Near even
                        self.advantage_label.setText(f"Predicted: Even (32-32) (50.0%)")
                        self.advantage_label.setStyleSheet("color: white; font-size: 8px; margin-top: 2px; background-color: transparent;")
                    
                    return  # Successfully used calibration
                    
            except Exception:
                # If calibration fails, fall back to fallback method
                pass
        
        # Fallback to the old method if calibration is not available
        self._fallback_prediction(weighted_advantage, confidence_factor)
    
    def _probability_to_score_difference(self, black_win_prob: float, pieces_remaining: int, confidence_factor: float) -> float:
        """Convert win probability to predicted score difference based on historical patterns"""
        # This method converts the calibrated win probability to a realistic score difference
        # The conversion is based on typical Othello game patterns
        
        # Adjust probability based on game stage and confidence
        # Early game: more uncertainty, late game: more precise
        adjusted_prob = 0.5 + (black_win_prob - 0.5) * confidence_factor
        
        # Convert probability to score difference
        # A 50% probability = 0 point difference
        # A 75% probability = roughly +8 point difference
        # A 25% probability = roughly -8 point difference
        
        # Use a sigmoid-like function for realistic conversion
        if adjusted_prob > 0.5:
            # Black advantage
            prob_diff = adjusted_prob - 0.5
            # Scale based on pieces remaining (more pieces = more potential for large differences)
            scale_factor = min(1.0, pieces_remaining / 30.0)  # Full scale after 30 pieces played
            score_diff = prob_diff * 16.0 * scale_factor  # Max 8 point difference
        else:
            # White advantage
            prob_diff = 0.5 - adjusted_prob
            scale_factor = min(1.0, pieces_remaining / 30.0)
            score_diff = -prob_diff * 16.0 * scale_factor  # Max -8 point difference
        
        # Ensure reasonable bounds
        score_diff = max(-25, min(25, score_diff))
        
        return score_diff
    
    def _fallback_prediction(self, advantage: int, confidence_factor: float):
        """Fallback prediction method when calibration is not available"""
        # Use a more stable scaling approach that doesn't jump around
        # In Othello, evaluation scores typically range from -2000 to +2000
        # We want to map this to realistic final score differences
        
        base_scale = 0.015  # 1000 points = 15 point difference
        scaled_advantage = advantage * base_scale
        
        # Apply confidence factor to reduce volatility in early game
        if confidence_factor < 0.5:
            scaled_advantage *= 0.8
        elif confidence_factor < 0.8:
            scaled_advantage *= 0.9
        
        # Ensure the prediction is within realistic bounds
        scaled_advantage = max(-25, min(25, scaled_advantage))
        
        # Calculate predicted final scores
        if scaled_advantage > 1:
            # Black advantage
            black_score = 32 + int(scaled_advantage)
            white_score = 32 - int(scaled_advantage)
            black_score = max(0, min(64, black_score))
            white_score = max(0, min(64, white_score))
            
            if confidence_factor < 0.3:
                confidence_text = " (Early)"
            elif confidence_factor < 0.7:
                confidence_text = " (Mid)"
            else:
                confidence_text = " (Late)"
                
            self.advantage_label.setText(f"Predicted: Black {black_score}-{white_score}{confidence_text}")
            self.advantage_label.setStyleSheet("color: #00ff00; font-size: 8px; margin-top: 2px; background-color: transparent;")
        elif scaled_advantage < -1:
            # White advantage
            white_score = 32 + int(abs(scaled_advantage))
            black_score = 32 - int(abs(scaled_advantage))
            white_score = max(0, min(64, white_score))
            black_score = max(0, min(64, black_score))
            
            if confidence_factor < 0.3:
                confidence_text = " (Early)"
            elif confidence_factor < 0.7:
                confidence_text = " (Mid)"
            else:
                confidence_text = " (Late)"
                
            self.advantage_label.setText(f"Predicted: White {white_score}-{black_score}{confidence_text}")
            self.advantage_label.setStyleSheet("color: #ff0000; font-size: 8px; margin-top: 2px; background-color: transparent;")
        else:
            # Near even
            self.advantage_label.setText("Predicted: Even (32-32)")
            self.advantage_label.setStyleSheet("color: white; font-size: 8px; margin-top: 2px; background-color: transparent;")
        
    def new_game(self):
        """Reset the graph for a new game"""
        self.advantage_history.clear()
        self.current_move = 0  # Reset to 0 for new game
        self.advantage_label.setText("Predicted: Even (32-32)")
        self.advantage_label.setStyleSheet("color: white; font-size: 8px; margin-top: 2px; background-color: transparent;")
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event for the graph"""
        if not self.advantage_history:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get widget dimensions
        widget_rect = self.rect()
        if widget_rect.width() <= 0 or widget_rect.height() <= 0:
            return
            
        # Calculate graph dimensions - maximize the plotting area
        # Use minimal margins to give maximum space to the graph
        margin = 8  # Reduced margins for more graph space
        top_margin = 35  # Reduced to give more space to the graph
        bottom_margin = 25  # Reduced to give more space to the graph
        graph_width = widget_rect.width() - 2 * margin
        graph_height = widget_rect.height() - top_margin - bottom_margin
        
        if graph_width <= 0 or graph_height <= 0:
            return
            
        # Y-axis: Fixed range from -64 to +64 for proper advantage representation
        y_min = -64
        y_max = 64
        y_range = y_max - y_min
        
        # X-axis scales from move 1 to the final move
        if self.advantage_history:
            x_min = 1  # Start from move 1
            x_max = max(move for move, _ in self.advantage_history)  # Final move number
            x_range = x_max - x_min
            if x_range == 0:  # Only one move, set range to 1
                x_range = 1
        else:
            x_min = 1
            x_max = 1
            x_range = 1
            
        # Draw grid lines
        painter.setPen(QPen(self.grid_color, 1))
        
        # Horizontal grid lines (5 lines for y-axis)
        for i in range(5):
            y = top_margin + (i * graph_height) // 4
            painter.drawLine(margin, y, margin + graph_width, y)
            
        # Vertical grid lines (5 lines for x-axis)
        for i in range(5):
            x = margin + (i * graph_width) // 4
            painter.drawLine(x, top_margin, x, top_margin + graph_height)
            
        # Draw zero line (always visible since 0 is within our y range)
        zero_y = top_margin + graph_height // 2  # 0 is at the middle
        painter.setPen(QPen(self.zero_line_color, 2))
        painter.drawLine(margin, zero_y, margin + graph_width, zero_y)
        
        # Draw axis labels - make them smaller and less intrusive with transparent backgrounds
        painter.setPen(self.axis_color)
        font = QFont()
        font.setPointSize(6)  # Smaller font to be less intrusive
        painter.setFont(font)
        
        # Set transparent background for all text
        painter.setBackgroundMode(Qt.BGMode.TransparentMode)
        
        # Y-axis labels (advantage values) - fixed range from -64 to +64
        for i in range(5):
            y = top_margin + (i * graph_height) // 4
            # Calculate the advantage value for this grid line
            # Top = +64, Middle = 0, Bottom = -64
            val = 64 - (i * 128) // 4
            # Format as pip difference
            if val > 0:
                label = f"+{val}"
            elif val < 0:
                label = f"{val}"
            else:
                label = "0"
            painter.drawText(2, y + 3, label)  # Reduced x offset
            
        # X-axis labels (move numbers) - scale from 1 to final move
        if x_range > 0:
            for i in range(5):
                x = margin + (i * graph_width) // 4
                move_num = int(x_min + (i * x_range) // 4)
                painter.drawText(x - 8, top_margin + graph_height + 12, str(move_num))  # Reduced y offset
        
        # Draw advantage line
        if len(self.advantage_history) > 1:
            painter.setPen(QPen(self.line_color, 2))
            
            points = []
            for move, score in self.advantage_history:
                # X coordinate: map move number to graph width
                # Move 1 maps to left edge, final move maps to right edge
                if x_range > 0:
                    x = margin + ((move - x_min) * graph_width) / x_range
                else:
                    x = margin + graph_width // 2  # Center if only one move
                
                # Y coordinate: map advantage score to graph height
                # Use trend-based weighted advantage to show game progression
                # Score maps from -64 (bottom) to +64 (top), with 0 at middle
                base_scale = 0.015  # Updated to match prediction logic
                
                # Calculate weighted advantage for this move (same logic as prediction)
                if move >= 2 and len(self.advantage_history) >= 3:
                    # Find the trend up to this move
                    move_index = next((i for i, (m, _) in enumerate(self.advantage_history) if m == move), 0)
                    if move_index >= 2:
                        # Get moves up to this point
                        moves_up_to_here = self.advantage_history[:move_index + 1]
                        if len(moves_up_to_here) >= 3:
                            recent_moves = moves_up_to_here[-3:]
                            move_nums = [m for m, _ in recent_moves]
                            scores = [s for _, s in recent_moves]
                            
                            if len(scores) >= 2:
                                trend = scores[-1] - scores[0]
                                trend_per_move = trend / max(1, move_nums[-1] - move_nums[0])
                                
                                # Project forward from this move
                                moves_remaining_from_here = max(0, 60 - move)
                                projected_advantage = score + (trend_per_move * moves_remaining_from_here * 0.5)
                                
                                # Check for significant change at this move (same logic as prediction)
                                significant_change = False
                                if move_index >= 1:
                                    prev_score = moves_up_to_here[move_index - 1][1]
                                    change_magnitude = abs(score - prev_score)
                                    if change_magnitude > 500:  # Same threshold as prediction
                                        significant_change = True
                                
                                if significant_change:
                                    # For significant changes, heavily weight the current score
                                    weighted_score = (score * 0.95) + (projected_advantage * 0.05)
                                else:
                                    # Normal weighting
                                    weighted_score = (score * 0.85) + (projected_advantage * 0.15)  # Updated to match prediction logic
                            else:
                                weighted_score = score
                        else:
                            weighted_score = score
                    else:
                        weighted_score = score
                else:
                    weighted_score = score
                
                scaled_score = max(-64, min(64, weighted_score * base_scale))
                y = top_margin + graph_height // 2 - (scaled_score * graph_height / 128)
                
                points.append((int(x), int(y)))
                
            # Draw line segments
            for i in range(1, len(points)):
                painter.drawLine(points[i-1][0], points[i-1][1], points[i][0], points[i][1])
                
            # Draw data points
            painter.setBrush(QBrush(self.line_color))
            for x, y in points:
                painter.drawEllipse(x - 3, y - 3, 6, 6)
        elif len(self.advantage_history) == 1:
            # Draw single point if only one move
            move, score = self.advantage_history[0]
            x = margin + graph_width // 2  # Center horizontally
            
            # Y coordinate: map advantage score to graph height
            # Use the same trend-based logic for consistency
            base_scale = 0.015  # Updated to match prediction logic
            weighted_score = score  # No trend data for single move
            scaled_score = max(-64, min(64, weighted_score * base_scale))
            y = top_margin + graph_height // 2 - (scaled_score * graph_height / 128)
            
            painter.setPen(QPen(self.line_color, 2))
            painter.setBrush(QBrush(self.line_color))
            painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)
                
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.update()
        
    def sizeHint(self):
        """Provide a size hint that maintains 16:9 aspect ratio"""
        return self.minimumSize()
