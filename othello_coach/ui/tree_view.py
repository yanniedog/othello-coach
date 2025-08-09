from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt6.QtCore import QUrl
from importlib import resources
import os
import json


class TreeView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        # Try WebEngine first, fallback to text display
        self._web_view = None
        self._text_view = None
        self._tree_data = None
        self._main_window = None  # Will be set by parent
        
        try:
            # Disable WebEngine when running in headless/offscreen environments (e.g., CI tests)
            if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
                raise ImportError("WebEngine disabled in offscreen mode")
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            self._web_view = QWebEngineView(self)
            # Load local viewer HTML if available
            try:
                idx = resources.files("othello_coach.config.web").joinpath("index.html")
                self._web_view.load(QUrl.fromLocalFile(str(idx)))
            except Exception:
                pass
            lay.addWidget(self._web_view)
        except Exception:
            # Fallback to text-based tree display
            lay.addWidget(QLabel("Tree Viewer (Text Mode)"))
            
            refresh_btn = QPushButton("Rebuild Tree")
            refresh_btn.clicked.connect(self._rebuild_tree)
            lay.addWidget(refresh_btn)
            
            self._text_view = QTextEdit()
            self._text_view.setReadOnly(True)
            self._text_view.setPlainText("Tree data will appear here when generated...")
            lay.addWidget(self._text_view)
    
    def set_main_window(self, main_window) -> None:
        """Set reference to main window for tree rebuilding."""
        self._main_window = main_window
    
    def update_tree_data(self, tree_data: dict) -> None:
        """Update the tree view with new tree data."""
        self._tree_data = tree_data
        if self._web_view:
            # TODO: Send data to web view via JavaScript bridge
            pass
        elif self._text_view:
            self._refresh_tree_display()
    
    def _refresh_tree_display(self) -> None:
        """Refresh the text-based tree display."""
        if not self._text_view or not self._tree_data:
            return
            
        text = "Game Tree:\n\n"
        text += f"Root: {self._tree_data.get('root', 'unknown')}\n"
        text += f"Nodes: {len(self._tree_data.get('nodes', {}))}\n"
        text += f"Edges: {len(self._tree_data.get('edges', []))}\n\n"
        
        # Show top nodes by score
        nodes = self._tree_data.get('nodes', {})
        if nodes:
            text += "Top nodes by score:\n"
            sorted_nodes = sorted(nodes.items(), key=lambda x: x[1].get('score', 0), reverse=True)
            for i, (hash_key, node) in enumerate(sorted_nodes[:10]):
                score = node.get('score', 0)
                stm = "Black" if node.get('stm') == 0 else "White"
                hash_str = str(hash_key)[:8] if isinstance(hash_key, int) else str(hash_key)[:8]
                text += f"{i+1}. Hash {hash_str}... Score: {score} (STM: {stm})\n"
        
        self._text_view.setPlainText(text)
    
    def _rebuild_tree(self) -> None:
        """Rebuild the tree by triggering the main window's action."""
        try:
            if self._main_window and hasattr(self._main_window, 'action_rebuild_tree'):
                print("Tree view: Triggering tree rebuild...")
                self._main_window.action_rebuild_tree.trigger()
            else:
                # Fallback: try to rebuild tree directly
                self._rebuild_tree_direct()
        except Exception as e:
            print(f"Tree rebuild failed: {e}")
            if self._text_view:
                self._text_view.setPlainText(f"Tree rebuild failed: {e}")
    
    def _rebuild_tree_direct(self) -> None:
        """Direct tree rebuild without main window reference."""
        try:
            # Import here to avoid circular imports
            from ..trees.builder import build_tree
            from ..engine.board import start_board
            
            # Use starting board if no main window reference
            board = start_board()
            if self._main_window and hasattr(self._main_window, 'board'):
                board = self._main_window.board.board
            
            print("Building tree directly...")
            tree_data = build_tree(board, "mobility_differential", depth=4, width=6, time_ms=1000)
            self.update_tree_data(tree_data)
            print(f"Tree rebuilt with {len(tree_data.get('nodes', {}))} nodes")
            
        except Exception as e:
            print(f"Direct tree rebuild failed: {e}")
            if self._text_view:
                self._text_view.setPlainText(f"Direct tree rebuild failed: {e}")
