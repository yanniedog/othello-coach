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
from ..logging_setup import setup_logging, install_qt_instrumentation, attach_window_instrumentation


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
    # Ensure logging is configured first
    setup_logging(overwrite=True)
    # Ensure config and DB exist
    install_and_init()

    # Only use offscreen if explicitly set, otherwise use default platform
    if "QT_QPA_PLATFORM" not in os.environ:
        pass

    app = QApplication([])

    # Load config and apply theme (default to dark)
    cfg = _load_config()
    ui_cfg = (cfg.get("ui", {}) or {})
    db_cfg = (cfg.get("db", {}) or {})
    theme_name = ui_cfg.get("theme", "dark")
    try:
        theme = load_theme(theme_name)
        # Modern, scalable stylesheet with accessible contrast and larger touch targets
        bg = theme.get('background', '#1e1e1e')
        fg = theme.get('foreground', '#f0f0f0')
        accent = theme.get('accent', '#4ea3ff')
        subtle = theme.get('subtle', '#2a2a2a')
        app.setStyleSheet(
            f"""
            QWidget {{ background-color: {bg}; color: {fg}; font-size: 13px; }}
            QToolBar {{ background: {subtle}; spacing: 8px; padding: 6px; border: 0; }}
            QStatusBar {{ background: {subtle}; }}
            QTabBar::tab {{ padding: 8px 14px; margin: 2px; }}
            QTabWidget::pane {{ border: 1px solid {subtle}; }}
            QPushButton {{ padding: 8px 14px; border-radius: 4px; background: {accent}; color: #0b0b0b; }}
            QPushButton:disabled {{ background: #777; color: #333; }}
            QGroupBox {{ border: 1px solid {subtle}; border-radius: 6px; margin-top: 10px; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
            QGraphicsView {{ background-color: {bg}; }}
            QSplitter::handle {{ background: {subtle}; width: 6px; }}
            QLabel#TitleLabel {{ font-weight: 600; font-size: 16px; }}
            """
        )
    except Exception:
        # If theme fails to load, continue with Qt defaults
        pass

    # Start DB writer early and expose queue on the app for other components
    db_queue: mp.Queue = mp.Queue()
    writer = DBWriter(
        db_path=str(DB_PATH),
        in_queue=db_queue,
        busy_timeout_ms=int(db_cfg.get("busy_timeout_ms", 4000)),
        wal_checkpoint_mb=int(db_cfg.get("wal_checkpoint_mb", 100)),
        per_position_cap=int(db_cfg.get("per_position_cap", 500)),
        auto_vacuum_days=int(db_cfg.get("auto_vacuum_days", 14)),
    )
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
    try:
        # Install Qt instrumentation after window created
        install_qt_instrumentation(app)
        attach_window_instrumentation(win)
    except Exception:
        pass
    return app.exec()
