import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PyQt6.QtWidgets import QApplication
from othello_coach.ui.main_window import MainWindow

app = QApplication([])
win = MainWindow()
print('title', win.windowTitle())
