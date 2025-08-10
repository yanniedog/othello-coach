from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
from dataclasses import dataclass
import logging
import time
import orjson
from ..logging_setup import get_log_path

CONFIG_HOME = pathlib.Path(os.path.expanduser("~/.othello_coach"))
CONFIG_PATH = CONFIG_HOME / "config.toml"
DB_PATH = CONFIG_HOME / "coach.sqlite"
DEFAULTS_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "defaults.toml"
SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[1] / "db" / "schema.sql"
CENTRAL_LOG_PATH = get_log_path()


@dataclass
class InitResult:
    config_created: bool
    db_created: bool


def ensure_config() -> bool:
    CONFIG_HOME.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULTS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        return True
    return False


def ensure_database() -> bool:
    created = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    try:
        with conn:
            for pragma in (
                "PRAGMA journal_mode=WAL;",
                "PRAGMA synchronous=NORMAL;",
                "PRAGMA cache_size=-131072;",
                "PRAGMA mmap_size=268435456;",
            ):
                conn.execute(pragma)
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    finally:
        conn.close()
    return created


def install_and_init() -> InitResult:
    cfg_new = ensure_config()
    db_new = ensure_database()
    if cfg_new or db_new:
        logging.getLogger(__name__).info("Initialised configuration and database")
    return InitResult(cfg_new, db_new)


def log_event(module: str, event: str, **kwargs) -> None:
    """Structured event logging through the central logger.

    Emits a single JSON line via the Python logging system so it reaches the
    central log file configured by logging_setup.setup_logging().
    """
    payload = {"ts": time.time(), "module": module, "event": event}
    payload.update(kwargs)
    try:
        line = orjson.dumps(payload).decode("utf-8")
        logging.getLogger(f"event.{module}").info(line)
    except Exception:
        logging.getLogger("event").exception("failed to log event: %s", {"module": module, "event": event})


def main() -> None:
    import argparse
    import zipfile
    import datetime as dt

    parser = argparse.ArgumentParser(prog="othello-diag")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--db-writer-log", default=str(CENTRAL_LOG_PATH), help="Deprecated; central log path used")
    args = parser.parse_args()

    install_and_init()

    bundle_path = pathlib.Path(args.bundle)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("config.toml", CONFIG_PATH.read_text(encoding="utf-8"))
        if DB_PATH.exists():
            z.write(DB_PATH, arcname="coach.sqlite")
        # include central log if present
        central_log = pathlib.Path(args.db_writer_log)
        if central_log.exists():
            z.write(central_log, arcname=CENTRAL_LOG_PATH.name)
        z.writestr("env.txt", f"python={sys.version}\nplatform={sys.platform}\n")
        z.writestr("timestamp.txt", dt.datetime.utcnow().isoformat())
    logging.getLogger(__name__).info("Diagnostics bundle written to %s", bundle_path)
