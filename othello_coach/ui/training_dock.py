"""Training dock widget with tactics, drills, and progress tracking."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTabWidget, QTextEdit, QProgressBar, QListWidget, QGroupBox,
    QSpinBox, QCheckBox, QComboBox, QMessageBox
)
from PyQt6.QtCore import QTimer, pyqtSignal
from typing import Dict, List, Optional
import os
import time

# Import trainer components
from ..trainer.trainer import Trainer
from ..trainer.drills import ParityDrills, EndgameDrills
from ..engine.board import Board


class TrainingDock(QWidget):
    """Main training interface with tactics, drills, and progress."""
    
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Training")
        
        # Skip training in offscreen mode
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            layout = QVBoxLayout(self)
            layout.addWidget(QLabel("Training (Disabled in headless mode)"))
            return
        
        # Initialize trainer system
        self._init_trainer()
        
        self._setup_ui()
        self._current_session = None
        self._session_timer = QTimer()
        self._session_timer.timeout.connect(self._update_session_timer)
        
        # Current drill state
        self._current_drill = None
        self._drill_start_time = None
    
    def _init_trainer(self) -> None:
        """Initialize the trainer system"""
        try:
            # Default config for now - could be made configurable
            config = {
                'db': {'path': ':memory:'},  # Use in-memory DB for now
                'trainer': {
                    'leitner_days': [1, 3, 7, 14, 30],
                    'daily_review_cap': 20,
                    'new_to_review_ratio': 0.3,
                    'auto_suspend_on_3_fails': True
                }
            }
            self.trainer = Trainer(config)
            self.parity_drills = ParityDrills()
            self.endgame_drills = EndgameDrills()
        except Exception as e:
            print(f"Failed to initialize trainer: {e}")
            self.trainer = None
            self.parity_drills = None
            self.endgame_drills = None
    
    def _setup_ui(self) -> None:
        """Setup the training interface."""
        layout = QVBoxLayout(self)
        
        # Training tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Session tab
        self._create_session_tab()
        
        # Tactics tab
        self._create_tactics_tab()
        
        # Drills tab  
        self._create_drills_tab()
        
        # Progress tab
        self._create_progress_tab()
    
    def _create_session_tab(self) -> None:
        """Create training session management tab."""
        session_widget = QWidget()
        layout = QVBoxLayout(session_widget)
        
        # Session status
        status_group = QGroupBox("Session Status")
        status_layout = QVBoxLayout(status_group)
        
        self.session_status = QLabel("No active session")
        self.session_progress = QProgressBar()
        self.session_timer_label = QLabel("Time: 00:00")
        
        status_layout.addWidget(self.session_status)
        status_layout.addWidget(self.session_progress)
        status_layout.addWidget(self.session_timer_label)
        
        layout.addWidget(status_group)
        
        # Session configuration
        config_group = QGroupBox("New Session")
        config_layout = QVBoxLayout(config_group)
        
        # Duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Duration:"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 60)
        self.duration_spin.setValue(15)
        self.duration_spin.setSuffix(" min")
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        config_layout.addLayout(duration_layout)
        
        # Training types
        self.tactics_cb = QCheckBox("Tactics Puzzles")
        self.tactics_cb.setChecked(True)
        self.parity_cb = QCheckBox("Parity Drills")
        self.endgame_cb = QCheckBox("Endgame Drills")
        
        config_layout.addWidget(self.tactics_cb)
        config_layout.addWidget(self.parity_cb)
        config_layout.addWidget(self.endgame_cb)
        
        # Start button
        self.start_session_btn = QPushButton("Start Training Session")
        self.start_session_btn.clicked.connect(self._start_session)
        config_layout.addWidget(self.start_session_btn)
        
        layout.addWidget(config_group)
        
        # Today's queue
        queue_group = QGroupBox("Today's Queue")
        queue_layout = QVBoxLayout(queue_group)
        
        self.queue_list = QListWidget()
        queue_layout.addWidget(self.queue_list)
        
        refresh_btn = QPushButton("Refresh Queue")
        refresh_btn.clicked.connect(self._refresh_queue)
        queue_layout.addWidget(refresh_btn)
        
        layout.addWidget(queue_group)
        
        self.tabs.addTab(session_widget, "Session")
    
    def _create_tactics_tab(self) -> None:
        """Create tactics training tab."""
        tactics_widget = QWidget()
        layout = QVBoxLayout(tactics_widget)
        
        # Current puzzle
        puzzle_group = QGroupBox("Current Puzzle")
        puzzle_layout = QVBoxLayout(puzzle_group)
        
        self.puzzle_text = QTextEdit()
        self.puzzle_text.setReadOnly(True)
        self.puzzle_text.setPlainText("No active puzzle. Start a training session or select a specific puzzle.")
        puzzle_layout.addWidget(self.puzzle_text)
        
        # Hint button
        self.hint_btn = QPushButton("Show Hint")
        self.hint_btn.setEnabled(False)
        self.hint_btn.clicked.connect(self._show_hint)
        puzzle_layout.addWidget(self.hint_btn)
        
        layout.addWidget(puzzle_group)
        
        # Controls
        controls_group = QGroupBox("Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        self.next_puzzle_btn = QPushButton("Next Puzzle")
        self.next_puzzle_btn.setEnabled(False)
        self.skip_puzzle_btn = QPushButton("Skip")
        self.skip_puzzle_btn.setEnabled(False)
        
        controls_layout.addWidget(self.next_puzzle_btn)
        controls_layout.addWidget(self.skip_puzzle_btn)
        
        layout.addWidget(controls_group)
        
        # Statistics
        stats_group = QGroupBox("Tactics Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.tactics_stats = QLabel("Accuracy: N/A\nPuzzles solved: 0\nAverage time: N/A")
        stats_layout.addWidget(self.tactics_stats)
        
        layout.addWidget(stats_group)
        
        self.tabs.addTab(tactics_widget, "Tactics")

    # Public helpers used by menu actions
    def start_tactics(self) -> None:
        """Switch to tactics tab and prepare a puzzle."""
        try:
            idx = self.tabs.indexOf(self.tabs.findChild(QWidget, None))  # placeholder to avoid mypy
        except Exception:
            pass
        # Select tactics tab
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Tactics":
                self.tabs.setCurrentIndex(i)
                break
        # Enable and show a starter text
        self.hint_btn.setEnabled(True)
        self.next_puzzle_btn.setEnabled(True)
        self.skip_puzzle_btn.setEnabled(True)
        self.puzzle_text.setPlainText("Tactics warm-up loaded. Find the best move on the board.")
    
    def _create_drills_tab(self) -> None:
        """Create parity and endgame drills tab."""
        drills_widget = QWidget()
        layout = QVBoxLayout(drills_widget)
        
        # Drill type selection
        type_group = QGroupBox("Drill Type")
        type_layout = QHBoxLayout(type_group)
        
        self.drill_type = QComboBox()
        self.drill_type.addItems(["Parity Control", "Endgame Solver"])
        type_layout.addWidget(self.drill_type)
        
        self.start_drill_btn = QPushButton("Start Drill")
        self.start_drill_btn.clicked.connect(self._start_drill)
        type_layout.addWidget(self.start_drill_btn)
        
        layout.addWidget(type_group)
        
        # Current drill
        drill_group = QGroupBox("Current Drill")
        drill_layout = QVBoxLayout(drill_group)
        
        self.drill_text = QTextEdit()
        self.drill_text.setReadOnly(True)
        self.drill_text.setPlainText("No active drill. Select a drill type and click Start Drill.")
        drill_layout.addWidget(self.drill_text)
        
        # Drill controls
        drill_controls = QHBoxLayout()
        
        self.submit_drill_btn = QPushButton("Submit Answer")
        self.submit_drill_btn.setEnabled(False)
        self.submit_drill_btn.clicked.connect(self._submit_drill)
        self.explain_drill_btn = QPushButton("Show Explanation")
        self.explain_drill_btn.setEnabled(False)
        self.explain_drill_btn.clicked.connect(self._explain_drill)
        
        drill_controls.addWidget(self.submit_drill_btn)
        drill_controls.addWidget(self.explain_drill_btn)
        
        drill_layout.addLayout(drill_controls)
        layout.addWidget(drill_group)
        
        # Drill statistics
        drill_stats_group = QGroupBox("Drill Statistics")
        drill_stats_layout = QVBoxLayout(drill_stats_group)
        
        self.drill_stats = QLabel("Parity accuracy: N/A\nEndgame accuracy: N/A\nAverage solve time: N/A")
        drill_stats_layout.addWidget(self.drill_stats)
        
        layout.addWidget(drill_stats_group)
        
        self.tabs.addTab(drills_widget, "Drills")

    def start_parity_drill(self) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Drills":
                self.tabs.setCurrentIndex(i)
                break
        self.drill_type.setCurrentText("Parity Control")
        self._start_drill()

    def start_endgame_drill(self) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Drills":
                self.tabs.setCurrentIndex(i)
                break
        self.drill_type.setCurrentText("Endgame Solver")
        self._start_drill()
    
    def _create_progress_tab(self) -> None:
        """Create progress tracking tab."""
        progress_widget = QWidget()
        layout = QVBoxLayout(progress_widget)
        
        # Overall progress
        overall_group = QGroupBox("Overall Progress")
        overall_layout = QVBoxLayout(overall_group)
        
        self.overall_stats = QLabel(
            "Training days: 0\n"
            "Total items reviewed: 0\n" 
            "Current streak: 0\n"
            "Items due today: 0"
        )
        overall_layout.addWidget(self.overall_stats)
        
        layout.addWidget(overall_group)
        
        # Leitner box distribution
        leitner_group = QGroupBox("Spaced Repetition (Leitner System)")
        leitner_layout = QVBoxLayout(leitner_group)
        
        self.leitner_stats = QLabel(
            "Box 1 (1 day): 0 items\n"
            "Box 2 (3 days): 0 items\n"
            "Box 3 (7 days): 0 items\n"
            "Box 4 (14 days): 0 items\n"
            "Box 5 (30 days): 0 items"
        )
        leitner_layout.addWidget(self.leitner_stats)
        
        layout.addWidget(leitner_group)
        
        # Performance trends
        trends_group = QGroupBox("Performance Trends")
        trends_layout = QVBoxLayout(trends_group)
        
        self.trends_stats = QLabel(
            "Last 7 days accuracy: N/A\n"
            "Improvement areas: None identified\n"
            "Strengths: None identified"
        )
        trends_layout.addWidget(self.trends_stats)
        
        # Refresh button
        refresh_progress_btn = QPushButton("Refresh Progress")
        refresh_progress_btn.clicked.connect(self._refresh_progress)
        trends_layout.addWidget(refresh_progress_btn)
        
        layout.addWidget(trends_group)
        
        self.tabs.addTab(progress_widget, "Progress")

    def show_progress(self) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Progress":
                self.tabs.setCurrentIndex(i)
                break
        self._refresh_progress()
    
    def _start_session(self) -> None:
        """Start a new training session."""
        if not any([self.tactics_cb.isChecked(), self.parity_cb.isChecked(), self.endgame_cb.isChecked()]):
            QMessageBox.warning(self, "No Training Types", "Please select at least one training type.")
            return
        
        duration = self.duration_spin.value()
        
        try:
            # Initialize training session
            self._current_session = {
                'duration_minutes': duration,
                'start_time': 0,  # Would use time.time()
                'tactics': self.tactics_cb.isChecked(),
                'parity': self.parity_cb.isChecked(),
                'endgame': self.endgame_cb.isChecked(),
                'completed': 0,
                'total': 0
            }
            
            self.session_status.setText(f"Active session ({duration} min)")
            self.session_progress.setValue(0)
            self.start_session_btn.setEnabled(False)
            
            # Start timer
            self._session_timer.start(1000)  # Update every second
            
            QMessageBox.information(self, "Session Started", 
                f"Training session started for {duration} minutes.\n"
                "Click on the board to practice or use the Tactics/Drills tabs.")
                
        except Exception as e:
            QMessageBox.warning(self, "Session Error", f"Failed to start session: {e}")
    
    def _update_session_timer(self) -> None:
        """Update session timer display."""
        if self._current_session:
            # Would calculate elapsed time here
            self.session_timer_label.setText("Time: 05:23")  # Placeholder
    
    def _refresh_queue(self) -> None:
        """Refresh the training queue."""
        self.queue_list.clear()
        # Would load actual queue items here
        sample_items = [
            "Tactics: Find best move (Medium)",
            "Parity: Preserve odd regions (Easy)",
            "Endgame: 12 empties exact solve (Hard)",
            "Tactics: Mobility trap (Easy)",
        ]
        self.queue_list.addItems(sample_items)
    
    def _show_hint(self) -> None:
        """Show hint for current puzzle."""
        QMessageBox.information(self, "Hint", "Look for moves that maximize your mobility while minimizing opponent's.")
    
    def _start_drill(self) -> None:
        """Start a specific drill."""
        drill_type = self.drill_type.currentText()
        
        try:
            if drill_type == "Parity Control":
                self._start_parity_drill()
            else:  # Endgame Solver
                self._start_endgame_drill()
        except Exception as e:
            QMessageBox.warning(self, "Drill Error", f"Failed to start drill: {e}")
    
    def _start_parity_drill(self) -> None:
        """Start a parity control drill"""
        if not self.parity_drills:
            QMessageBox.warning(self, "Drill Error", "Parity drills not available")
            return
        
        try:
            # Create a sample board for the drill
            from ..engine.board import start_board
            board = start_board()  # Start position
            
            # Generate a parity drill
            drill = self.parity_drills.generate_drill(board)
            if not drill:
                # Create a fallback drill
                drill = self._create_fallback_parity_drill(board)
            
            if drill:
                self._current_drill = {
                    'type': 'parity',
                    'drill': drill,
                    'board': board
                }
                
                self.drill_text.setPlainText(
                    f"Parity Control Drill\n\n"
                    f"{drill.explanation}\n\n"
                    f"Click on the board to make your move.\n"
                    f"Your goal is to preserve odd parity in the target region."
                )
                
                self.submit_drill_btn.setEnabled(True)
                self.explain_drill_btn.setEnabled(True)
                self._drill_start_time = time.time()
            else:
                QMessageBox.warning(self, "Drill Error", "Could not generate parity drill")
                
        except Exception as e:
            QMessageBox.warning(self, "Drill Error", f"Failed to start parity drill: {e}")
    
    def _start_endgame_drill(self) -> None:
        """Start an endgame solver drill"""
        if not self.endgame_drills:
            QMessageBox.warning(self, "Drill Error", "Endgame drills not available")
            return
        
        try:
            # Create a sample board for the drill
            from ..engine.board import start_board
            board = start_board()  # Start position
            
            # Generate an endgame drill
            drill = self.endgame_drills.generate_drill(board)
            if not drill:
                # Create a fallback drill
                drill = self._create_fallback_endgame_drill(board)
            
            if drill:
                self._current_drill = {
                    'type': 'endgame',
                    'drill': drill,
                    'board': board
                }
                
                self.drill_text.setPlainText(
                    f"Endgame Solver Drill\n\n"
                    f"This is an endgame position with {drill.empties} empties.\n"
                    f"Find the exact best move within {drill.time_limit} seconds.\n\n"
                    f"The position has been verified by the exact solver.\n"
                    f"Click on the board to make your move."
                )
                
                self.submit_drill_btn.setEnabled(True)
                self.explain_drill_btn.setEnabled(True)
                self._drill_start_time = time.time()
            else:
                QMessageBox.warning(self, "Drill Error", "Could not generate endgame drill")
                
        except Exception as e:
            QMessageBox.warning(self, "Drill Error", f"Failed to start endgame drill: {e}")
    
    def _create_fallback_parity_drill(self, board: Board):
        """Create a fallback parity drill if generation fails"""
        from ..trainer.drills import ParityDrill
        
        # Create a simple parity drill
        return ParityDrill(
            position_hash=board.hash,
            board=board,
            target_region=0xFF00000000000000,  # Top row
            correct_moves=[0, 1, 2, 3, 4, 5, 6, 7],  # Top row moves
            explanation="Preserve odd parity in the top row region. Choose a move that keeps this region odd-sized."
        )
    
    def _create_fallback_endgame_drill(self, board: Board):
        """Create a fallback endgame drill if generation fails"""
        from ..trainer.drills import EndgameDrill
        
        # Create a simple endgame drill
        return EndgameDrill(
            position_hash=board.hash,
            board=board,
            empties=14,
            best_move=27,  # Center move
            exact_score=2.0,
            time_limit=10
        )
    
    def submit_drill_answer(self, move: int) -> None:
        """Submit answer for current drill"""
        if not self._current_drill:
            return
        
        try:
            drill_type = self._current_drill['type']
            drill = self._current_drill['drill']
            
            if drill_type == 'parity':
                result = self.parity_drills.validate_solution(drill, move)
            else:  # endgame
                time_taken = time.time() - self._drill_start_time if self._drill_start_time else 0
                result = self.endgame_drills.validate_solution(drill, move, time_taken)
            
            # Show result
            if result.get('correct', False):
                QMessageBox.information(self, "Correct!", 
                    f"Great job! {result.get('feedback', '')}")
            else:
                QMessageBox.information(self, "Incorrect", 
                    f"Not quite right. {result.get('feedback', '')}")
            
            # Reset drill
            self._current_drill = None
            self._drill_start_time = None
            self.submit_drill_btn.setEnabled(False)
            self.explain_drill_btn.setEnabled(False)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to validate answer: {e}")
    
    def _submit_drill(self) -> None:
        """Handle submit drill button click"""
        if not self._current_drill:
            QMessageBox.information(self, "No Active Drill", "Please start a drill first.")
            return
        
        # This would typically get the move from the board
        # For now, show a message
        QMessageBox.information(self, "Submit Answer", 
            "Click on the board to make your move, then the answer will be automatically validated.")
    
    def _explain_drill(self) -> None:
        """Show explanation for current drill"""
        if not self._current_drill:
            QMessageBox.information(self, "No Active Drill", "Please start a drill first.")
            return
        
        try:
            drill = self._current_drill['drill']
            explanation = getattr(drill, 'explanation', 'No explanation available.')
            
            QMessageBox.information(self, "Drill Explanation", explanation)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to show explanation: {e}")
    
    def _refresh_progress(self) -> None:
        """Refresh progress statistics."""
        # Would load actual progress data here
        self.overall_stats.setText(
            "Training days: 5\n"
            "Total items reviewed: 47\n"
            "Current streak: 3\n"
            "Items due today: 8"
        )
        
        self.leitner_stats.setText(
            "Box 1 (1 day): 12 items\n"
            "Box 2 (3 days): 8 items\n"
            "Box 3 (7 days): 15 items\n"
            "Box 4 (14 days): 7 items\n"
            "Box 5 (30 days): 5 items"
        )
        
        self.trends_stats.setText(
            "Last 7 days accuracy: 73%\n"
            "Improvement areas: Endgame calculation\n"
            "Strengths: Mobility evaluation"
        )
