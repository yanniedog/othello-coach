from __future__ import annotations

import os
import pathlib
import sqlite3
import sys
from dataclasses import dataclass

from rich.console import Console

console = Console()

CONFIG_HOME = pathlib.Path(os.path.expanduser("~/.othello_coach"))
CONFIG_PATH = CONFIG_HOME / "config.toml"
DB_PATH = CONFIG_HOME / "coach.sqlite"
DEFAULTS_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "defaults.toml"
SCHEMA_PATH = pathlib.Path(__file__).resolve().parents[1] / "db" / "schema.sql"


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
        console.print("[green]Initialised configuration and database[/green]")
    return InitResult(cfg_new, db_new)


def main() -> None:
    import argparse
    import zipfile
    import datetime as dt

    parser = argparse.ArgumentParser(prog="othello-diag")
    parser.add_argument("--bundle", required=True)
    args = parser.parse_args()

    install_and_init()

    bundle_path = pathlib.Path(args.bundle)
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("config.toml", CONFIG_PATH.read_text(encoding="utf-8"))
        if DB_PATH.exists():
            z.write(DB_PATH, arcname="coach.sqlite")
        z.writestr("env.txt", f"python={sys.version}\nplatform={sys.platform}\n")
        z.writestr("timestamp.txt", dt.datetime.utcnow().isoformat())
    console.print(f"[green]Diagnostics bundle written to {bundle_path}[/green]")
