from __future__ import annotations

import os
from PyQt6.QtWidgets import QApplication
from .main_window import MainWindow


def run_app() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    app = QApplication([])
    win = MainWindow()
    win.show()
    return app.exec()
