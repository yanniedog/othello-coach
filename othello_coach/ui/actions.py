from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow


def register_actions(win: QMainWindow) -> None:
    win.action_new = QAction("New", win)
    win.addAction(win.action_new)
