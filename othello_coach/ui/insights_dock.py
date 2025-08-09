from __future__ import annotations

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QCheckBox
from PyQt6.QtCore import pyqtSignal


class InsightsDock(QWidget):
    overlays_changed = pyqtSignal(dict)
    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("Insights"))
        # Overlay toggles per spec
        self.mobility_cb = QCheckBox("Mobility heat")
        self.parity_cb = QCheckBox("Parity map")
        self.stability_cb = QCheckBox("Stability heat")
        self.corner_cb = QCheckBox("Corner tension")
        for cb in (self.mobility_cb, self.parity_cb, self.stability_cb, self.corner_cb):
            cb.setChecked(False)
            cb.stateChanged.connect(self._emit_overlays)
            lay.addWidget(cb)

    def _emit_overlays(self) -> None:
        self.overlays_changed.emit(
            {
                "mobility": self.mobility_cb.isChecked(),
                "parity": self.parity_cb.isChecked(),
                "stability": self.stability_cb.isChecked(),
                "corner": self.corner_cb.isChecked(),
            }
        )
