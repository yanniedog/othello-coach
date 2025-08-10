from __future__ import annotations

import logging
import pathlib
import sys
import threading
import time
import traceback
from typing import Any, Iterable, Optional

try:
    from PyQt6.QtCore import QObject, QEvent, qInstallMessageHandler
    from PyQt6.QtGui import QAction
    from PyQt6.QtWidgets import QApplication, QMenu, QWidget
except Exception:  # pragma: no cover - allows non-Qt contexts (e.g., CLI/tests)
    QObject = object  # type: ignore
    QEvent = None  # type: ignore
    qInstallMessageHandler = None  # type: ignore
    QAction = None  # type: ignore
    QApplication = None  # type: ignore
    QMenu = None  # type: ignore
    QWidget = None  # type: ignore


LOG_FILE_NAME = "othello-coach.log"


def get_log_path() -> pathlib.Path:
    return pathlib.Path.cwd() / LOG_FILE_NAME


def setup_logging(overwrite: bool = True, level: int = logging.DEBUG) -> None:
    """Configure root logging to a single file in the current working directory.

    - Overwrites the log file on first setup (per process) if overwrite is True
    - Adds a STDERR handler for immediate visibility
    - Installs sys.excepthook and threading excepthook
    - Redirects stdout/stderr into logging
    - Captures warnings via logging
    """
    log_path = get_log_path()

    # Prevent duplicate handlers on re-entry
    root_logger = logging.getLogger()
    if getattr(root_logger, "_oc_logging_configured", False):
        return

    fmt = "%(asctime)s.%(msecs)03d %(levelname)s [%(process)d:%(threadName)s] %(name)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    handlers: list[logging.Handler] = []
    file_mode = "w" if overwrite else "a"
    file_handler = logging.FileHandler(log_path, mode=file_mode, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handlers.append(file_handler)

    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    handlers.append(stderr_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)
    root_logger._oc_logging_configured = True  # type: ignore[attr-defined]

    # Capture warnings through logging
    logging.captureWarnings(True)

    # Install exception hooks
    sys.excepthook = _log_unhandled_exception  # type: ignore[assignment]
    try:
        threading.excepthook = _log_thread_exception  # type: ignore[attr-defined]
    except Exception:
        pass

    # Redirect stdout/stderr to logging so prints are captured
    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO)  # type: ignore[assignment]
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR)  # type: ignore[assignment]


def _log_unhandled_exception(exc_type, exc_value, exc_tb) -> None:  # type: ignore[no-untyped-def]
    logger = logging.getLogger("unhandled")
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical("Unhandled exception:\n%s", tb_str)


def _log_thread_exception(args) -> None:  # type: ignore[no-untyped-def]
    # Python 3.8+: threading.ExceptHookArgs
    logger = logging.getLogger("thread")
    tb_str = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    logger.critical("Unhandled thread exception in %s:\n%s", getattr(args, "thread", None), tb_str)


class _StreamToLogger:
    def __init__(self, logger: logging.Logger, level: int) -> None:
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message: str) -> None:
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self.logger.log(self.level, line)

    def flush(self) -> None:
        if self._buffer:
            self.logger.log(self.level, self._buffer)
            self._buffer = ""


class GuiEventLogger(QObject):
    """Global Qt event filter to record all user interactions and UI visibility changes."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        super().__init__()
        self.logger = logger or logging.getLogger("qt.events")

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:  # type: ignore[override]
        try:
            et = event.type()
            name = getattr(obj, "objectName", lambda: "")() or obj.__class__.__name__

            # Mouse clicks
            if et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                self._log_mouse_event(name, obj, event)

            # Key presses
            elif et in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease, QEvent.Type.Shortcut):
                self.logger.info("key_event: widget=%s type=%s", name, et.name if hasattr(et, "name") else int(et))

            # Focus changes
            elif et in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
                self.logger.info("focus: widget=%s type=%s", name, "in" if et == QEvent.Type.FocusIn else "out")

            # Widget show/hide
            elif et in (QEvent.Type.Show, QEvent.Type.Hide):
                self.logger.info("visibility: widget=%s event=%s", name, "show" if et == QEvent.Type.Show else "hide")

            # Menu shown: enumerate entries
            if QMenu is not None and isinstance(obj, QMenu) and et == QEvent.Type.Show:
                try:
                    actions = obj.actions()
                    items = [
                        {
                            "text": (a.text() or "").replace("\t", " ").replace("&", ""),
                            "checkable": a.isCheckable(),
                            "checked": a.isChecked(),
                            "enabled": a.isEnabled(),
                        }
                        for a in actions
                        if isinstance(a, QAction)
                    ]
                    self.logger.info("menu_show: title=%s items=%s", obj.title(), items)
                except Exception:
                    pass
        except Exception:
            logging.getLogger("qt.events").exception("eventFilter failure")
        # Do not swallow the event
        return False

    def _log_mouse_event(self, name: str, obj: QObject, event: QEvent) -> None:
        try:
            # Late import to avoid hard Qt deps if unused
            from PyQt6.QtCore import Qt  # noqa
            from PyQt6.QtGui import QMouseEvent  # noqa
        except Exception:
            self.logger.info("mouse_event: widget=%s", name)
            return
        try:
            me = event  # type: ignore[assignment]
            button = getattr(me, "button", lambda: None)()
            pos = getattr(me, "position", lambda: None)()
            btn_name = str(button) if button is not None else "?"
            coords = (float(pos.x()), float(pos.y())) if pos is not None else (None, None)
            text = getattr(obj, "text", lambda: "")()
            self.logger.info("mouse: widget=%s btn=%s pos=%s text=%s", name, btn_name, coords, text)
        except Exception:
            self.logger.info("mouse_event: widget=%s", name)


def install_qt_instrumentation(app: QApplication) -> None:
    """Install Qt message handler and a global event filter to capture GUI activity."""
    logger = logging.getLogger("qt")

    # Route Qt internal messages to Python logging
    if qInstallMessageHandler is not None:
        def _qt_msg_handler(mode, context, message):  # type: ignore[no-untyped-def]
            level = logging.INFO
            if str(mode).endswith("WarningMsg"):
                level = logging.WARNING
            elif str(mode).endswith("CriticalMsg"):
                level = logging.ERROR
            elif str(mode).endswith("FatalMsg"):
                level = logging.CRITICAL
            logger.log(level, "qt: %s", message)

        try:
            qInstallMessageHandler(_qt_msg_handler)  # type: ignore[arg-type]
        except Exception:
            logger.exception("Failed to install Qt message handler")

    # Global event filter for all widgets
    try:
        ev = GuiEventLogger()
        app.installEventFilter(ev)
        # Keep a reference to avoid GC
        app.setProperty("_oc_event_logger", ev)
        logging.getLogger(__name__).info("Installed global GUI event logger")
    except Exception:
        logging.getLogger(__name__).exception("Failed to install GUI event filter")


def attach_window_instrumentation(window: QWidget) -> None:
    """Attach signals on menus and actions to capture interactions.

    - Connect QAction.triggered to log action activations
    - Connect QMenu.aboutToShow/aboutToHide
    """
    lg = logging.getLogger("qt.ui")
    try:
        # Connect all actions found under the window hierarchy
        if QAction is not None:
            actions: Iterable[QAction] = window.findChildren(QAction)  # type: ignore[assignment]
            for a in actions:
                try:
                    a.triggered.connect(lambda checked=False, act=a: lg.info("action_triggered: text=%s checked=%s", (act.text() or "").replace("&", ""), act.isChecked()))  # type: ignore[attr-defined]
                except Exception:
                    pass
        # Hook menus
        if QMenu is not None:
            menus: Iterable[QMenu] = window.findChildren(QMenu)  # type: ignore[assignment]
            for m in menus:
                try:
                    m.aboutToShow.connect(lambda m=m: lg.info("menu_about_to_show: title=%s", m.title()))  # type: ignore[attr-defined]
                    m.aboutToHide.connect(lambda m=m: lg.info("menu_about_to_hide: title=%s", m.title()))  # type: ignore[attr-defined]
                except Exception:
                    pass
        lg.info("Window instrumentation attached: %s", window.__class__.__name__)
    except Exception:
        lg.exception("Failed to attach window instrumentation")


