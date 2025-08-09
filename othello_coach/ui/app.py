from __future__ import annotations

import atexit
import os
import multiprocessing as mp
from typing import Any, Dict

from PyQt6.QtWidgets import QApplication

from .main_window import MainWindow
from ..tools.diag import install_and_init, CONFIG_PATH, DB_PATH
from ..db.writer import DBWriter
from .themes import load_theme


def _load_config() -> Dict[str, Any]:
    # Parse TOML config; prefer stdlib tomllib (3.11+), else tomli (added as dep)
    try:
        import tomllib  # type: ignore[attr-defined]
        with open(CONFIG_PATH, "rb") as f:  # type: ignore[arg-type]
            return tomllib.load(f)
    except ModuleNotFoundError:
        try:
            import tomli  # type: ignore
            with open(CONFIG_PATH, "rb") as f:  # type: ignore[arg-type]
                return tomli.load(f)
        except Exception:
            return {}
    except Exception:
        return {}


def run_app() -> int:
    # Ensure config and DB exist
    install_and_init()

    # Only use offscreen if explicitly set, otherwise use default platform
    if "QT_QPA_PLATFORM" not in os.environ:
        pass

    app = QApplication([])

    # Load config and apply theme (default to dark)
    cfg = _load_config()
    theme_name = (cfg.get("ui", {}) or {}).get("theme", "dark")
    try:
        theme = load_theme(theme_name)
        # Basic stylesheet application; detailed WCAG checks happen in themes module if needed
        app.setStyleSheet(
            f"""
            QWidget {{ background-color: {theme.get('background', '#1e1e1e')}; color: {theme.get('foreground', '#f0f0f0')}; }}
            QGraphicsView {{ background-color: {theme.get('background', '#1e1e1e')}; }}
            """
        )
    except Exception:
        # If theme fails to load, continue with Qt defaults
        pass

    # Start DB writer early and expose queue on the app for other components
    db_queue: mp.Queue = mp.Queue()
    writer = DBWriter(str(DB_PATH), db_queue)
    writer.start()

    def _shutdown_writer() -> None:
        try:
            db_queue.put({"op": "shutdown"})
        except Exception:
            pass
        # Give the writer some time to exit
        try:
            writer.join(timeout=2.0)
        except Exception:
            pass

    atexit.register(_shutdown_writer)
    app.setProperty("db_queue", db_queue)

    win = MainWindow()
    win.show()
    return app.exec()
