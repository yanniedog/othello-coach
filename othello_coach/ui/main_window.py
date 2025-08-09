from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QHBoxLayout
from .board_widget import BoardWidget
from .insights_dock import InsightsDock
from .tree_view import TreeView


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        # Ensure a QApplication exists even in headless/unit-test contexts
        if QApplication.instance() is None:
            # Create a lightweight app; tests set QT_QPA_PLATFORM=offscreen
            QApplication([])
        super().__init__()
        self.setWindowTitle("Othello Coach")
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.addWidget(BoardWidget())
        right = QVBoxLayout()
        right.addWidget(InsightsDock())
        right.addWidget(TreeView())
        w = QWidget()
        w.setLayout(right)
        layout.addWidget(w)
        self.setCentralWidget(root)
