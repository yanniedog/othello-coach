# Othello Coach

Local, private Othello/Reversi coach with strong engine, insights, trees, and a Qt UI. No network calls.

Quick start

- Windows PowerShell
  - Create venv: `python -m venv .venv; . .\.venv\Scripts\Activate.ps1`
  - Install: `pip install -e .`
  - Perft: `othello-perft --depth 2`
  - GUI: `othello-coach`

CLI tools

- Perft with move list input:
  - `othello-perft --depth 3 --position e6d6c5`

Diagnostics

- Create initial config and DB and bundle diagnostics:
  - `othello-diag --bundle diag.zip`
