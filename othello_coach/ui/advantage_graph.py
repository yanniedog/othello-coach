from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
import math
from typing import List, Tuple

from ..engine.board import Board
from ..engine.eval import evaluate_position


class AdvantageGraphWidget(QWidget):
    """Real-time graph showing comparative advantage between players"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)  # Reduced from 300x200
        self.setMaximumSize(250, 200)  # Add maximum size constraint
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)  # Changed from Expanding to Fixed
        
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
        
        # Labels
        self.setup_labels()
        
        # Update timer for smooth animations
        self.update_timer = QTimer()
        self.update_timer.setInterval(50)  # 20 FPS
        self.update_timer.timeout.connect(self.update)
        
    def setup_labels(self):
        """Setup the widget layout with labels"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)  # Reduced from 10,10,10,10
        
        # Title
        title_label = QLabel("Predicted Final Score")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)  # Reduced from 12
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white; margin-bottom: 3px;")  # Reduced margin
        layout.addWidget(title_label)
        
        # Legend
        legend_layout = QHBoxLayout()
        
        black_label = QLabel("Black Advantage")
        black_label.setStyleSheet("color: white; font-size: 8px;")  # Reduced from 10px
        legend_layout.addWidget(black_label)
        
        legend_layout.addStretch()
        
        white_label = QLabel("White Advantage")
        white_label.setStyleSheet("color: white; font-size: 8px;")  # Reduced from 10px
        legend_layout.addWidget(white_label)
        
        layout.addLayout(legend_layout)
        
        # Add some spacing before the graph area
        layout.addSpacing(5)  # Reduced from 10
        
        # Current advantage display
        self.advantage_label = QLabel("Predicted: Even (32-32)")
        self.advantage_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.advantage_label.setStyleSheet("color: white; font-size: 9px; margin-top: 3px;")  # Reduced font and margin
        layout.addWidget(self.advantage_label)
        
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
        """Update the advantage label with predicted final score"""
        # Scale the advantage to a reasonable final score difference
        # The maximum possible final score difference in Othello is 64-0 = 64
        # We'll scale the advantage to fit within reasonable bounds
        
        # First, normalize the advantage to a reasonable range
        # Most evaluation scores are between -1000 and +1000, so we'll scale accordingly
        # Use a more aggressive scaling factor to get realistic pip differences
        normalized_advantage = advantage / 2000.0  # Normalize to -0.5 to +0.5
        
        # Scale to a reasonable final score difference (max 32 points difference)
        # This ensures we stay within realistic bounds
        score_diff = int(normalized_advantage * 32)
        
        # Ensure the score difference is reasonable and doesn't exceed valid bounds
        score_diff = max(-32, min(32, score_diff))
        
        if score_diff > 0:
            # Black advantage: show predicted final score like "Black 42-22"
            black_score = 32 + score_diff
            white_score = 32 - score_diff
            # Ensure scores are within valid range (0-64)
            black_score = max(0, min(64, black_score))
            white_score = max(0, min(64, white_score))
            self.advantage_label.setText(f"Predicted: Black {black_score}-{white_score}")
            self.advantage_label.setStyleSheet("color: #00ff00; font-size: 9px; margin-top: 3px;")
        elif score_diff < 0:
            # White advantage: show predicted final score like "White 42-22"
            white_score = 32 + abs(score_diff)
            black_score = 32 - abs(score_diff)
            # Ensure scores are within valid range (0-64)
            white_score = max(0, min(64, white_score))
            black_score = max(0, min(64, black_score))
            self.advantage_label.setText(f"Predicted: White {white_score}-{black_score}")
            self.advantage_label.setStyleSheet("color: #ff0000; font-size: 9px; margin-top: 3px;")
        else:
            self.advantage_label.setText("Predicted: Even (32-32)")
            self.advantage_label.setStyleSheet("color: white; font-size: 9px; margin-top: 3px;")
        
    def new_game(self):
        """Reset the graph for a new game"""
        self.advantage_history.clear()
        self.current_move = 0  # Reset to 0 for new game
        self.advantage_label.setText("Predicted: Even (32-32)")
        self.advantage_label.setStyleSheet("color: white; font-size: 9px; margin-top: 3px;")  # Reduced font size
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
            
        # Calculate graph dimensions (accounting for margins and labels)
        margin = 15  # Reduced from 20
        top_margin = 45  # Reduced from 60 (space for title and legend)
        bottom_margin = 25  # Reduced from 40 (space for advantage label)
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
        
        # Draw axis labels
        painter.setPen(self.axis_color)
        font = QFont()
        font.setPointSize(7)  # Reduced from 8
        painter.setFont(font)
        
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
            painter.drawText(5, y + 4, label)
            
        # X-axis labels (move numbers) - scale from 1 to final move
        if x_range > 0:
            for i in range(5):
                x = margin + (i * graph_width) // 4
                move_num = int(x_min + (i * x_range) // 4)
                painter.drawText(x - 10, top_margin + graph_height + 15, str(move_num))
        
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
                # Score maps from -64 (bottom) to +64 (top), with 0 at middle
                # Clamp score to valid range and scale heuristic values appropriately
                # Heuristic scores can be very large (e.g., +125, +108), so scale them down
                scaled_score = max(-64, min(64, score / 20.0))  # Scale heuristic scores down
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
            # Scale heuristic scores down to fit within -64 to +64 range
            scaled_score = max(-64, min(64, score / 20.0))
            y = top_margin + graph_height // 2 - (scaled_score * graph_height / 128)
            
            painter.setPen(QPen(self.line_color, 2))
            painter.setBrush(QBrush(self.line_color))
            painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)
                
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self.update()
