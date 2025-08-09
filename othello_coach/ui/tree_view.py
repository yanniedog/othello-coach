from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class TreeView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        # Minimal placeholder; roadmap requires WebEngine fallback if unavailable
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
            self._view = QWebEngineView(self)
            lay.addWidget(self._view)
        except Exception:
            lay.addWidget(QLabel("Tree (WebEngine unavailable)"))
