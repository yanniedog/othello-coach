from __future__ import annotations

import sys
from .diag import install_and_init


def main() -> None:
    install_and_init()
    from othello_coach.ui.app import run_app

    sys.exit(run_app())
