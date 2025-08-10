#!/usr/bin/env python3
"""Test script for the advantage graph widget"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer

from othello_coach.ui.advantage_graph import AdvantageGraphWidget
from othello_coach.engine.board import start_board, make_move
from othello_coach.engine.movegen_ref import legal_moves_mask

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advantage Graph Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Create advantage graph
        self.advantage_graph = AdvantageGraphWidget()
        layout.addWidget(self.advantage_graph)
        
        # Create test buttons
        button_layout = QVBoxLayout()
        
        self.new_game_btn = QPushButton("New Game")
        self.new_game_btn.clicked.connect(self.new_game)
        button_layout.addWidget(self.new_game_btn)
        
        self.make_move_btn = QPushButton("Make Random Move")
        self.make_move_btn.clicked.connect(self.make_random_move)
        button_layout.addWidget(self.make_move_btn)
        
        self.reset_btn = QPushButton("Reset Graph")
        self.reset_btn.clicked.connect(self.reset_graph)
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize board
        self.board = start_board()
        self.advantage_graph.update_advantage(self.board)
        
        # Timer for automatic moves
        self.timer = QTimer()
        self.timer.timeout.connect(self.make_random_move)
        
        self.auto_btn = QPushButton("Start Auto Play")
        self.auto_btn.clicked.connect(self.toggle_auto_play)
        button_layout.addWidget(self.auto_btn)
        
        self.auto_playing = False
        
    def new_game(self):
        """Start a new game"""
        self.board = start_board()
        self.advantage_graph.new_game()
        self.advantage_graph.update_advantage(self.board)
        
    def make_random_move(self):
        """Make a random legal move"""
        legal = legal_moves_mask(self.board)
        if legal == 0:
            print("No legal moves available")
            return
            
        # Convert bitboard to move list
        moves = []
        m = legal
        while m:
            lsb = m & -m
            moves.append(lsb.bit_length() - 1)
            m ^= lsb
            
        if moves:
            move = moves[0]  # Just take first legal move for simplicity
            self.board, _ = make_move(self.board, move)
            self.advantage_graph.update_advantage(self.board)
            print(f"Made move {move} at ply {self.board.ply}")
            
    def reset_graph(self):
        """Reset the advantage graph"""
        self.advantage_graph.new_game()
        
    def toggle_auto_play(self):
        """Toggle automatic move generation"""
        if self.auto_playing:
            self.timer.stop()
            self.auto_btn.setText("Start Auto Play")
            self.auto_playing = False
        else:
            self.timer.start(1000)  # 1 second intervals
            self.auto_btn.setText("Stop Auto Play")
            self.auto_playing = True

def main():
    app = QApplication(sys.argv)
    
    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #2b2b2b;
            color: white;
        }
        QPushButton {
            background-color: #404040;
            color: white;
            border: 1px solid #555;
            padding: 8px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #303030;
        }
    """)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
