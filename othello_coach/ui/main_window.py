from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout

from .board_widget import BoardWidget
from .insights_dock import InsightsDock
from .tree_view import TreeView
from .actions import register_actions


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        # Ensure a QApplication exists even in headless/unit-test contexts
        if QApplication.instance() is None:
            # Create a lightweight app; tests set QT_QPA_PLATFORM=offscreen
            QApplication([])
        super().__init__()
        self.setWindowTitle("Othello Coach")

        # Central layout: Board (left), right column with Insights + Tree
        root = QWidget()
        layout = QHBoxLayout(root)

        self.board = BoardWidget()
        layout.addWidget(self.board, stretch=2)

        right_col = QVBoxLayout()
        self.insights = InsightsDock()
        self.tree = TreeView()
        right_col.addWidget(self.insights, stretch=1)
        right_col.addWidget(self.tree, stretch=1)
        right_widget = QWidget()
        right_widget.setLayout(right_col)
        layout.addWidget(right_widget, stretch=1)

        self.setCentralWidget(root)

        # Actions and shortcuts per spec
        register_actions(self)
        self._wire_shortcuts()
        # Wire overlays toggle to board
        self.insights.overlays_changed.connect(self.board.apply_overlays)

    def _wire_shortcuts(self) -> None:
        # Map keys to actions as per spec where applicable (subset for now)
        self.action_new.setShortcut("N")
        # Additional shortcuts would be wired here (Z/Y undo/redo, arrows, Space, O, T)
