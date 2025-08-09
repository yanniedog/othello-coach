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
    # Quick keys for overlays per spec (O toggles all)
    def _toggle_all() -> None:
        try:
            dock = getattr(win, "insights", None)
            if dock is None:
                return
            on = not dock.mobility_cb.isChecked()
            dock.mobility_cb.setChecked(on)
            dock.parity_cb.setChecked(on)
            dock.stability_cb.setChecked(on)
            dock.corner_cb.setChecked(on)
        except Exception:
            pass
    win.action_toggle_overlays.triggered.connect(_toggle_all)
    # Rebuild tree
    win.action_rebuild_tree = QAction("Rebuild Tree", win)
    win.addAction(win.action_rebuild_tree)
