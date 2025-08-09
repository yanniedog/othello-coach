#!/usr/bin/env python3
"""Visual test of the GUI - open a window and test features."""

import sys
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    
    # Create main widget
    main_widget = QWidget()
    main_widget.setWindowTitle("Othello Coach - Feature Test")
    main_widget.resize(1000, 600)
    
    layout = QVBoxLayout(main_widget)
    
    # Add instruction label
    instructions = QLabel("""
    GUI Feature Test:
    1. Click buttons below to test each feature
    2. Check if overlays appear on the board
    3. Test keyboard shortcuts: N (new), O (toggle overlays), T (tree)
    """)
    layout.addWidget(instructions)
    
    # Import and add main window
    from othello_coach.ui.main_window import MainWindow
    othello_window = MainWindow()
    layout.addWidget(othello_window)
    
    # Add test buttons
    button_layout = QHBoxLayout()
    
    def test_mobility():
        print("Testing mobility overlay...")
        othello_window.insights.mobility_cb.setChecked(not othello_window.insights.mobility_cb.isChecked())
        print(f"Mobility overlay: {othello_window.board.overlay_flags['mobility']}")
    
    def test_stability():
        print("Testing stability overlay...")
        othello_window.insights.stability_cb.setChecked(not othello_window.insights.stability_cb.isChecked())
        print(f"Stability overlay: {othello_window.board.overlay_flags['stability']}")
    
    def test_parity():
        print("Testing parity overlay...")
        othello_window.insights.parity_cb.setChecked(not othello_window.insights.parity_cb.isChecked())
        print(f"Parity overlay: {othello_window.board.overlay_flags['parity']}")
    
    def test_corner():
        print("Testing corner overlay...")
        othello_window.insights.corner_cb.setChecked(not othello_window.insights.corner_cb.isChecked())
        print(f"Corner overlay: {othello_window.board.overlay_flags['corner']}")
    
    def test_new_game():
        print("Testing new game...")
        from othello_coach.engine.board import start_board
        old_board = str(othello_window.board.board)
        othello_window.action_new.trigger()
        new_board = str(othello_window.board.board)
        print(f"Board changed: {old_board != new_board}")
        print(f"Game over reset: {not othello_window.board.game_over}")
    
    def test_tree():
        print("Testing tree rebuild...")
        othello_window.action_rebuild_tree.trigger()
        print("Tree rebuild triggered")
    
    mob_btn = QPushButton("Toggle Mobility")
    mob_btn.clicked.connect(test_mobility)
    button_layout.addWidget(mob_btn)
    
    stab_btn = QPushButton("Toggle Stability")
    stab_btn.clicked.connect(test_stability)
    button_layout.addWidget(stab_btn)
    
    par_btn = QPushButton("Toggle Parity")
    par_btn.clicked.connect(test_parity)
    button_layout.addWidget(par_btn)
    
    corner_btn = QPushButton("Toggle Corner")
    corner_btn.clicked.connect(test_corner)
    button_layout.addWidget(corner_btn)
    
    new_btn = QPushButton("New Game")
    new_btn.clicked.connect(test_new_game)
    button_layout.addWidget(new_btn)
    
    tree_btn = QPushButton("Rebuild Tree")
    tree_btn.clicked.connect(test_tree)
    button_layout.addWidget(tree_btn)
    
    layout.addLayout(button_layout)
    
    # Show window
    main_widget.show()
    
    # Also make a move to test overlays with a different position
    def make_test_move():
        print("Making test move...")
        try:
            from othello_coach.engine.board import make_move
            othello_window.board.board, _ = make_move(othello_window.board.board, 19)  # d3
            othello_window.board._draw()
            print("Test move made - overlays should be more visible now")
        except Exception as e:
            print(f"Error making test move: {e}")
    
    # Make test move after 2 seconds
    from PyQt6.QtCore import QTimer
    QTimer.singleShot(2000, make_test_move)
    
    print("GUI Test Window opened. Test the features and see if they work visually.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
