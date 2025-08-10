from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton
from PyQt6.QtCore import QUrl
from importlib import resources
import os
import json
import logging


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
            # Render a proper graph using Cytoscape when WebEngine is available
            try:
                payload_js = json.dumps(self._tree_data)
                js = (
                    "(function(){"
                    f"var parsed={payload_js};"
                    "var nodes=[];var edges=[];"
                    "for (var key in parsed.nodes){nodes.push({data:{id:String(key), score:parsed.nodes[key].score}});}"
                    "parsed.edges.forEach(function(e){edges.push({data:{source:String(e.from), target:String(e.to), move:e.move, score:e.score}});});"
                    "if (window.cy){cy.destroy();}"
                    "var container=document.getElementById('app');"
                    "window.cy = cytoscape({container:container, elements:nodes.concat(edges), style:["
                    "{ selector:'node', style:{ 'label':'data(score)', 'background-color':'#4ea3ff', 'width':8, 'height':8 }},"
                    "{ selector:'edge', style:{ 'width':1, 'line-color':'#999', 'target-arrow-color':'#999', 'curve-style':'bezier' }}],"
                    "layout:{ name:'breadthfirst', directed:true, roots:String(parsed.root) }});"
                    "})();"
                )
                self._web_view.page().runJavaScript(js)  # type: ignore[attr-defined]
            except Exception:
                # Fallback silently to text
                logging.getLogger(__name__).exception("WebEngine render failed; falling back to text")
                self._refresh_tree_display()
        elif self._text_view:
            self._refresh_tree_display()
    
    def _refresh_tree_display(self) -> None:
        """Refresh the text-based tree display."""
        if not self._text_view or not self._tree_data:
            return
            
        text = "Game Tree (hierarchical):\n\n"
        nodes = self._tree_data.get('nodes', {})
        edges = self._tree_data.get('edges', [])
        root = self._tree_data.get('root')

        # Build adjacency list to render as an actual tree (transpositions will repeat nodes)
        children = {}
        for e in edges:
            children.setdefault(e['from'], []).append(e['to'])
        
        def render(node_id, indent, visited):
            # Avoid infinite loops on transpositions; allow limited repeats
            if visited.get(node_id, 0) > 1:
                return
            visited[node_id] = visited.get(node_id, 0) + 1
            n = nodes.get(node_id, {})
            score = n.get('score', 0)
            text_lines.append("  " * indent + f"- {str(node_id)[:8]} (score {score})")
            for ch in children.get(node_id, [])[:12]:
                render(ch, indent + 1, visited)

        text_lines = [f"Root: {root}", f"Nodes: {len(nodes)}", f"Edges: {len(edges)}", ""]
        if root in nodes:
            render(root, 0, {})
        else:
            # If root missing, just list top-level nodes
            for nid in list(nodes.keys())[:20]:
                text_lines.append(f"- {str(nid)[:8]} (score {nodes[nid].get('score', 0)})")

        text = "\n".join(text_lines)
        
        self._text_view.setPlainText(text)
    
    def _rebuild_tree(self) -> None:
        """Rebuild the tree by triggering the main window's action."""
        try:
            if self._main_window and hasattr(self._main_window, 'action_rebuild_tree'):
                logging.getLogger(__name__).info("Tree view: Triggering tree rebuild...")
                self._main_window.action_rebuild_tree.trigger()
            else:
                # Fallback: try to rebuild tree directly
                self._rebuild_tree_direct()
        except Exception as e:
            logging.getLogger(__name__).exception("Tree rebuild failed: %s", e)
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
            
            logging.getLogger(__name__).info("Building tree directly...")
            tree_data = build_tree(board, "mobility_differential", depth=4, width=6, time_ms=1000)
            self.update_tree_data(tree_data)
            logging.getLogger(__name__).info("Tree rebuilt with %s nodes", len(tree_data.get('nodes', {})))
            
        except Exception as e:
            logging.getLogger(__name__).exception("Direct tree rebuild failed: %s", e)
            if self._text_view:
                self._text_view.setPlainText(f"Direct tree rebuild failed: {e}")
