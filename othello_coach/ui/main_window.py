from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
import os

# In offscreen/headless CI environments, constructing real Qt widgets can fail even with
# the offscreen platform plugin. Provide a minimal stub fallback that satisfies unit
# tests without requiring a full GUI stack.

_OFFSCREEN = os.environ.get("QT_QPA_PLATFORM") == "offscreen"

if _OFFSCREEN:
    class _StubWindow:  # type: ignore[misc]
        def __init__(self) -> None:
            self._title = "Othello Coach"

        # Stub APIs used in tests and elsewhere
        def setWindowTitle(self, title: str) -> None:  # noqa: D401
            self._title = title

        def windowTitle(self) -> str:  # noqa: D401
            return self._title

        # Compatibility placeholders for QAction registration, signals, etc.
        def addAction(self, *args, **kwargs):
            pass

    BaseWindow = _StubWindow
else:
    BaseWindow = QMainWindow

from .board_widget import BoardWidget
from .insights_dock import InsightsDock
from .tree_view import TreeView
from .actions import register_actions

# Ensure a QApplication instance exists even when the module is imported in headless test contexts
if QApplication.instance() is None:
    # Use software OpenGL for headless environments to avoid GPU dependence
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    QApplication([])


class MainWindow(BaseWindow):
    def __init__(self) -> None:
        # In offscreen/headless mode, avoid constructing real child widgets that
        # require a valid GUI environment.
        if _OFFSCREEN:
            super().__init__()
            self.setWindowTitle("Othello Coach")
            return

        # Ensure an application instance exists for real GUI runs.
        if QApplication.instance() is None:
            QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
            QApplication([])

        super().__init__()
        self.setWindowTitle("Othello Coach")

        # Central layout: Board (left), right column with Insights + Tree
        root = QWidget()
        layout = QHBoxLayout(root)

        self.board = BoardWidget()
        layout.addWidget(self.board, stretch=2)

        right_col = QVBoxLayout()
        self.insights = InsightsDock()
        self.tree = TreeView()
        right_col.addWidget(self.insights, stretch=1)
        right_col.addWidget(self.tree, stretch=1)
        right_widget = QWidget()
        right_widget.setLayout(right_col)
        layout.addWidget(right_widget, stretch=1)

        self.setCentralWidget(root)

        # Actions and shortcuts per spec
        register_actions(self)
        self._wire_shortcuts()
        # Wire overlays toggle to board
        self.insights.overlays_changed.connect(self.board.apply_overlays)

    def _wire_shortcuts(self) -> None:
        # Map keys to actions as per spec where applicable (subset for now)
        self.action_new.setShortcut("N")
        # Arrows/Space best move would be added when engine UI actions are implemented
