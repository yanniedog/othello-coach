import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

def test_ui_smoke():
    from othello_coach.ui.app import run_app
    # Can't run event loop in test; just import window
    from othello_coach.ui.main_window import MainWindow
    w = MainWindow()
    assert w.windowTitle() == "Othello Coach"
