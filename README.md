## Othello Coach

Local, private Othello/Reversi coach that plays at multiple strengths, explains moves, visualises overlays, builds goal-directed trees, and persists knowledge. No network calls. Cross‑platform.

Quick start
- Create a Python 3.12 venv, activate it, and install: `pip install -e .[graphviz]`
- Launch GUI: `othello-coach`
- Perft sanity: `othello-perft --depth 3`

Config
- User config at `~/.othello_coach/config.toml` created on first run from `othello_coach/config/defaults.toml`.

CLI
- `othello-coach` – GUI
- `othello-perft` – perft driver
- `othello-tree` – tree builder
- `othello-diag` – diagnostics bundle

License
- MIT
