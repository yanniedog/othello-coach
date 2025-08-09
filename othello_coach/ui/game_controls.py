from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QGroupBox, QSpinBox
)
from PyQt6.QtCore import pyqtSignal

from ..engine.strength import list_strength_profiles


class GameControlsWidget(QWidget):
    """Widget for game mode controls and CPU settings"""
    
    # Signals
    game_mode_changed = pyqtSignal(str)
    cpu_strength_changed = pyqtSignal(str, str)  # black_strength, white_strength
    cpu_delay_changed = pyqtSignal(int)
    new_game_requested = pyqtSignal()
    
    def __init__(self) -> None:
        super().__init__()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # Game Mode Selection
        mode_group = QGroupBox("Game Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Human vs Human",
            "Human vs CPU", 
            "CPU vs CPU"
        ])
        self.mode_combo.setCurrentText("Human vs Human")
        mode_layout.addWidget(QLabel("Players:"))
        mode_layout.addWidget(self.mode_combo)
        
        layout.addWidget(mode_group)
        
        # CPU Strength Settings
        self.cpu_group = QGroupBox("CPU Settings")
        cpu_layout = QVBoxLayout(self.cpu_group)
        
        # Black CPU strength
        black_layout = QHBoxLayout()
        black_layout.addWidget(QLabel("Black CPU:"))
        self.black_strength_combo = QComboBox()
        strength_profiles = list_strength_profiles()
        self.black_strength_combo.addItems(strength_profiles)
        self.black_strength_combo.setCurrentText("elo_1400")
        black_layout.addWidget(self.black_strength_combo)
        cpu_layout.addLayout(black_layout)
        
        # White CPU strength
        white_layout = QHBoxLayout()
        white_layout.addWidget(QLabel("White CPU:"))
        self.white_strength_combo = QComboBox()
        self.white_strength_combo.addItems(strength_profiles)
        self.white_strength_combo.setCurrentText("elo_1400")
        white_layout.addWidget(self.white_strength_combo)
        cpu_layout.addLayout(white_layout)
        
        # CPU move delay
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("CPU delay:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(0, 5000)
        self.delay_spin.setSingleStep(100)
        self.delay_spin.setValue(1000)
        self.delay_spin.setSuffix(" ms")
        delay_layout.addWidget(self.delay_spin)
        cpu_layout.addLayout(delay_layout)
        
        layout.addWidget(self.cpu_group)
        
        # Game Control Buttons
        buttons_group = QGroupBox("Game Controls")
        buttons_layout = QVBoxLayout(buttons_group)
        
        self.new_game_btn = QPushButton("New Game")
        buttons_layout.addWidget(self.new_game_btn)
        
        layout.addWidget(buttons_group)
        
        # Game Status
        self.status_group = QGroupBox("Game Status")
        status_layout = QVBoxLayout(self.status_group)
        
        self.status_label = QLabel("Black to move")
        self.score_label = QLabel("Black: 2  White: 2")
        self.thinking_label = QLabel("")
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.score_label)
        status_layout.addWidget(self.thinking_label)
        
        layout.addWidget(self.status_group)
        
        # Initially disable CPU settings
        self._update_cpu_controls_visibility()
    
    def _connect_signals(self) -> None:
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.black_strength_combo.currentTextChanged.connect(self._on_strength_changed)
        self.white_strength_combo.currentTextChanged.connect(self._on_strength_changed)
        self.delay_spin.valueChanged.connect(self.cpu_delay_changed.emit)
        self.new_game_btn.clicked.connect(self.new_game_requested.emit)
    
    def _on_mode_changed(self) -> None:
        """Handle game mode change"""
        mode_text = self.mode_combo.currentText()
        mode_map = {
            "Human vs Human": "human_vs_human",
            "Human vs CPU": "human_vs_cpu",
            "CPU vs CPU": "cpu_vs_cpu"
        }
        mode = mode_map.get(mode_text, "human_vs_human")
        self._update_cpu_controls_visibility()
        self.game_mode_changed.emit(mode)
    
    def _on_strength_changed(self) -> None:
        """Handle CPU strength change"""
        black_strength = self.black_strength_combo.currentText()
        white_strength = self.white_strength_combo.currentText()
        self.cpu_strength_changed.emit(black_strength, white_strength)
    
    def _update_cpu_controls_visibility(self) -> None:
        """Show/hide CPU controls based on game mode"""
        mode_text = self.mode_combo.currentText()
        show_cpu = mode_text in ["Human vs CPU", "CPU vs CPU"]
        self.cpu_group.setVisible(show_cpu)
    
    def update_game_state(self, state: dict) -> None:
        """Update the display based on game state"""
        move_no = state.get("ply", 0) + 1  # Upcoming move number for the side to move
        # Update status
        if state.get("game_over", False):
            winner = state.get("winner", "Draw")
            if winner == "Draw":
                self.status_label.setText("Game Over - Draw!")
            else:
                self.status_label.setText(f"Game Over - {winner} wins!")
            self.thinking_label.setText("")
        else:
            to_move = state.get("to_move", "Black")
            if state.get("cpu_thinking", False):
                self.status_label.setText(f"Move {move_no} — {to_move} to move")
                self.thinking_label.setText("CPU is thinking...")
            else:
                self.status_label.setText(f"Move {move_no} — {to_move} to move")
                # Check if this is a pass situation
                last_move_info = state.get("last_move_info", "")
                if "pass" in last_move_info.lower():
                    self.thinking_label.setText(f"Previous: {last_move_info}")
                else:
                    self.thinking_label.setText("")
        
        # Update score
        black_count = state.get("black_count", 2)
        white_count = state.get("white_count", 2)
        self.score_label.setText(f"Black: {black_count}  White: {white_count}")
