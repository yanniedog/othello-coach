from __future__ import annotations

import argparse
import sys
from .diag import install_and_init
from othello_coach.db.writer import DBWriter


def main() -> None:
    p = argparse.ArgumentParser(prog="othello-coach")
    p.add_argument("--db-writer-log", default=None, help="Path to DB writer JSON log file")
    args, rest = p.parse_known_args()

    install_and_init()
    # Start DB writer process early so logs capture app startup, too
    # In a fuller app we'd share a Queue; here we only demonstrate startup with logging configured
    # The UI would be responsible for passing the queue and shutting down gracefully
    # For now, just run the app
    from othello_coach.ui.app import run_app

    sys.exit(run_app())
