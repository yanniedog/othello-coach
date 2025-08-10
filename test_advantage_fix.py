#!/usr/bin/env python3
"""Test script to verify advantage graph fixes"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt6.QtCore import Qt

# Add the othello_coach package to the path
sys.path.insert(0, '.')

from othello_coach.ui.advantage_graph import AdvantageGraphWidget
from othello_coach.engine.board import Board, start_board, make_move

class TestWindow(QMainWindow):
    __test__ = False
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advantage Graph Fix Test")
        self.setGeometry(100, 100, 400, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Add status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        self.advantage_graph = AdvantageGraphWidget()
        layout.addWidget(self.advantage_graph)
        
        # Test buttons
        test_button = QPushButton("Test Initial Position (ply=0)")
        test_button.clicked.connect(self.test_initial_position)
        layout.addWidget(test_button)
        
        test_button2 = QPushButton("Test First Move (ply=1)")
        test_button2.clicked.connect(self.test_first_move)
        layout.addWidget(test_button2)
        
        test_button3 = QPushButton("Test Second Move (ply=2)")
        test_button3.clicked.connect(self.test_second_move)
        layout.addWidget(test_button3)
        
        test_button4 = QPushButton("New Game")
        test_button4.clicked.connect(self.new_game)
        layout.addWidget(test_button4)
        
        # Initialize board
        self.board = start_board()
        self.status_label.setText(f"Board ply: {self.board.ply}")
        
    def test_initial_position(self):
        """Test the initial board position (ply=0)"""
        self.status_label.setText(f"Testing initial position, ply: {self.board.ply}")
        self.advantage_graph.update_advantage(self.board)
        print(f"Initial position added to history: {self.advantage_graph.advantage_history}")
        
    def test_first_move(self):
        """Test making the first move (ply=1)"""
        # Make a move to d3 (square 19)
        try:
            self.board, _ = make_move(self.board, 19)
            self.status_label.setText(f"First move made, ply: {self.board.ply}")
            self.advantage_graph.update_advantage(self.board)
            print(f"First move added to history: {self.advantage_graph.advantage_history}")
        except Exception as e:
            self.status_label.setText(f"Error making move: {e}")
            
    def test_second_move(self):
        """Test making the second move (ply=2)"""
        # Make a move to e3 (square 20)
        try:
            self.board, _ = make_move(self.board, 20)
            self.status_label.setText(f"Second move made, ply: {self.board.ply}")
            self.advantage_graph.update_advantage(self.board)
            print(f"Second move added to history: {self.advantage_graph.advantage_history}")
        except Exception as e:
            self.status_label.setText(f"Error making move: {e}")
            
    def new_game(self):
        """Start a new game"""
        self.advantage_graph.new_game()
        self.board = start_board()
        self.status_label.setText(f"New game started, ply: {self.board.ply}")
        print("New game started")

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; color: white; }
        QPushButton { background-color: #404040; color: white; border: 1px solid #606060; padding: 8px; margin: 4px; }
        QPushButton:hover { background-color: #505050; }
        QLabel { color: white; margin: 4px; }
    """)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
