#!/usr/bin/env python3
"""Test script to verify advantage graph display functionality"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import Qt

# Add the othello_coach package to the path
sys.path.insert(0, '.')

from othello_coach.ui.advantage_graph import AdvantageGraphWidget
from othello_coach.engine.board import Board, start_board

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advantage Graph Test")
        self.setGeometry(100, 100, 400, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.advantage_graph = AdvantageGraphWidget()
        layout.addWidget(self.advantage_graph)
        
        # Test buttons
        test_button = QPushButton("Test Black Advantage +3")
        test_button.clicked.connect(self.test_black_advantage)
        layout.addWidget(test_button)
        
        test_button2 = QPushButton("Test White Advantage +5")
        test_button2.clicked.connect(self.test_white_advantage)
        layout.addWidget(test_button2)
        
        test_button3 = QPushButton("Test Even Position")
        test_button3.clicked.connect(self.test_even_position)
        layout.addWidget(test_button3)
        
        test_button4 = QPushButton("Test Large Advantage +15")
        test_button4.clicked.connect(self.test_large_advantage)
        layout.addWidget(test_button4)
        
        # Add button to simulate multiple moves
        multi_move_button = QPushButton("Simulate 5 Moves")
        multi_move_button.clicked.connect(self.simulate_multiple_moves)
        layout.addWidget(multi_move_button)
        
        # Add button to start new game
        new_game_button = QPushButton("New Game")
        new_game_button.clicked.connect(self.new_game)
        layout.addWidget(new_game_button)
        
        self.board = start_board()
        self.move_counter = 0
        
    def test_black_advantage(self):
        self.move_counter += 1
        # Create a board with move number
        test_board = Board(self.board.B, self.board.W, self.board.stm, self.move_counter, self.board.hash)
        self.advantage_graph.update_advantage(test_board)
        print(f"Testing Black advantage at move {self.move_counter}")
        
    def test_white_advantage(self):
        self.move_counter += 1
        # Create a board with move number
        test_board = Board(self.board.B, self.board.W, self.board.stm, self.move_counter, self.board.hash)
        self.advantage_graph.update_advantage(test_board)
        print(f"Testing White advantage at move {self.move_counter}")
        
    def test_even_position(self):
        self.move_counter += 1
        # Create a board with move number
        test_board = Board(self.board.B, self.board.W, self.board.stm, self.move_counter, self.board.hash)
        self.advantage_graph.update_advantage(test_board)
        print(f"Testing even position at move {self.move_counter}")
        
    def test_large_advantage(self):
        self.move_counter += 1
        # Create a board with move number
        test_board = Board(self.board.B, self.board.W, self.board.stm, self.move_counter, self.board.hash)
        self.advantage_graph.update_advantage(test_board)
        print(f"Testing large advantage at move {self.move_counter}")
        
    def simulate_multiple_moves(self):
        """Simulate multiple moves to test x-axis scaling"""
        for i in range(5):
            self.move_counter += 1
            # Create a board with move number
            test_board = Board(self.board.B, self.board.W, self.board.stm, self.move_counter, self.board.hash)
            self.advantage_graph.update_advantage(test_board)
        print(f"Simulated 5 moves, total moves: {self.move_counter}")
        
    def new_game(self):
        """Start a new game"""
        self.advantage_graph.new_game()
        self.move_counter = 0
        print("Started new game")

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; color: white; }
        QPushButton { background-color: #404040; color: white; border: 1px solid #606060; padding: 8px; margin: 4px; }
        QPushButton:hover { background-color: #505050; }
    """)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
