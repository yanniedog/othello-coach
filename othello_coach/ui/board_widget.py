from __future__ import annotations

from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene


class BoardWidget(QGraphicsView):
    def __init__(self) -> None:
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setMinimumSize(300, 300)
