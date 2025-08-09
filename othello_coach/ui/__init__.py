# UI package

"""Package initialisation ensures a minimal QApplication exists.

This allows headless unit tests (e.g. QT_QPA_PLATFORM=offscreen) to import
UI modules that create QWidget subclasses without requiring the caller to
explicitly construct a QApplication first.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication, Qt

# In CI/offscreen mode, force software OpenGL to avoid GPU/driver needs.
if QApplication.instance() is None:
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL)
    QApplication([])