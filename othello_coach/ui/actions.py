from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow


def register_actions(win: QMainWindow) -> None:
    # New game
    win.action_new = QAction("New", win)
    win.addAction(win.action_new)
    # Undo / Redo (placeholders)
    win.action_undo = QAction("Undo", win)
    win.action_redo = QAction("Redo", win)
    win.addAction(win.action_undo)
    win.addAction(win.action_redo)
    # Toggle overlays
    win.action_toggle_overlays = QAction("Toggle Overlays", win)
    win.addAction(win.action_toggle_overlays)
    # Rebuild tree
    win.action_rebuild_tree = QAction("Rebuild Tree", win)
    win.addAction(win.action_rebuild_tree)
