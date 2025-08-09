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
            
            refresh_btn = QPushButton("Refresh Tree")
            refresh_btn.clicked.connect(self._refresh_tree_display)
            lay.addWidget(refresh_btn)
            
            self._text_view = QTextEdit()
            self._text_view.setReadOnly(True)
            self._text_view.setPlainText("Tree data will appear here when generated...")
            lay.addWidget(self._text_view)
    
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
