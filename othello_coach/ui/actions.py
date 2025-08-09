from __future__ import annotations

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow


def register_actions(win: QMainWindow) -> None:
    # New game
    win.action_new = QAction("New", win)
    win.addAction(win.action_new)
    
    def _new_game() -> None:
        try:
            if hasattr(win, "board"):
                from ..engine.board import start_board
                win.board.board = start_board()
                win.board.game_over = False
                win.board._ensure_playable_state()
                win.board._draw()
                print("New game started")
        except Exception as e:
            print(f"New game failed: {e}")
            import traceback
            traceback.print_exc()
    win.action_new.triggered.connect(_new_game)
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
    win.action_toggle_overlays.setShortcut("O")
    # Tree rebuild action per roadmap (shortcut T)
    win.action_rebuild_tree = QAction("Rebuild Tree", win)
    win.addAction(win.action_rebuild_tree)
    win.action_rebuild_tree.setShortcut("T")
    
    def _rebuild_tree() -> None:
        try:
            if hasattr(win, "board") and hasattr(win, "tree"):
                from ..trees.builder import build_tree
                tree_data = build_tree(win.board.board, "mobility_differential", depth=4, width=6, time_ms=1000)
                # Pass data to tree view
                if hasattr(win.tree, "update_tree_data"):
                    win.tree.update_tree_data(tree_data)
                print(f"Tree rebuilt with {len(tree_data.get('nodes', {}))} nodes")
        except Exception as e:
            print(f"Tree rebuild failed: {e}")
            import traceback
            traceback.print_exc()
    win.action_rebuild_tree.triggered.connect(_rebuild_tree)
    # Basic Undo/Redo shortcuts (Z/Y)
    win.action_undo.setShortcut("Z")
    win.action_redo.setShortcut("Y")
