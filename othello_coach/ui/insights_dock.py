from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class InsightsDock(QWidget):
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Insights"))
