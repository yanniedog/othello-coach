# Othello Coach v1.1

A local, private Othello/Reversi coach with advanced analysis, training, and performance acceleration.

## What's New in v1.1

### 🚀 Rust Acceleration
- **3-8× performance boost** with optional Rust kernel for hot paths
- Extended endgame solver: ≤16 empties (vs ≤12 in v1.0)
- Automatic fallback to Python when Rust unavailable

### 📝 Goal Definition Language (GDL)
- **Programmable tree building** with custom goals
- Syntax: `score(side=white)`, `min_opp_mob`, `custom(weights={mobility:0.5, parity:0.3})`
- Built-in authoring UI with syntax help and validation

### 🔍 Novelty Radar
- **Discover interesting lines** using sequence shingles
- Transposition-aware similarity detection
- Ranks candidates by novelty and engine interest

### 🎓 Training System
- **Tactics 2.0**: Generated from high-delta positions with contextual hints
- **Parity drills**: Interactive region control training
- **Endgame drills**: Exact solver verification (≤16 empties)
- **Spaced repetition**: Leitner system with adaptive scheduling

### ⚔️ Calibration & Gauntlets
- **Self-play tournaments** with configurable profiles
- **Glicko-2 rating system** with confidence intervals
- **Automated depth↔ELO mapping** with statistical validation
- **Win probability curves** for improved rationale weighting

### 🌐 Local API (Optional)
- **REST endpoints** for analysis, tree building, and search
- **Loopback-only** (127.0.0.1) for security
- **Token authentication** with rate limiting
- **OpenAPI documentation** (debug mode)

### 🐘 PostgreSQL Support (Optional)
- **Scalable backend** with table partitioning
- **Migration tools** from SQLite
- **Full-text search** using PostgreSQL's capabilities

## Installation

### Prerequisites
- Python 3.10+ [[memory:5655667]]
- Optional: Rust toolchain for acceleration
- Optional: PostgreSQL for scalable backend

### Basic Installation
```bash
# Clone and install
git clone <repository>
cd othello-coach
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -e .
```

### With Rust Acceleration
```bash
# Install Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build Rust kernel
cd rust_kernel
python build.py

# Verify acceleration
python -c "import rust_kernel; print('Rust acceleration available!')"
```

### With PostgreSQL
```bash
# Install PostgreSQL dependencies
pip install psycopg2-binary

# Configure in ~/.othello_coach/config.toml:
[feature_flags]
postgres = true

[postgres]
dsn = "postgresql://user:pass@localhost/othello_coach"
```

## Quick Start

### Launch GUI
```bash
othello-coach
```

### CLI Tools
```bash
# Self-play gauntlet
othello-selfplay --games 100 --workers 4 --profiles elo_400 elo_800 elo_1400

# Build tree with GDL
othello-tree --gdl "score(side=white) max_depth=10" --out tree.json

# Start local API
othello-api --port 8080

# Performance testing
othello-perft --depth 6
```

### GDL Examples
```gdl
# Maximize white's evaluation
score(side=white) max_depth=8 width=12

# Minimize opponent mobility
min_opp_mob prefer=corners

# Custom weighted goal
custom(weights={mobility:0.6, stability:0.3, parity:0.1})
max_depth=10 width=15

# Early corner capture
earliest_corner(max_plies=6) prefer=stability
```

## Configuration

Located at `~/.othello_coach/config.toml`:

```toml
[engine]
accel_enabled = true           # Use Rust acceleration
endgame_exact_empties = 16     # Extended with acceleration

[feature_flags]
gdl_authoring = true           # Enable GDL authoring UI
novelty_radar = true           # Enable novelty detection
trainer = true                 # Enable training system
gauntlet = true               # Enable gauntlets
api = false                   # Disable API by default
postgres = false              # Use SQLite by default

[trainer]
daily_review_cap = 30
leitner_days = [1,3,7,14,30]
auto_suspend_on_3_fails = true

[api]
bind = "127.0.0.1"
port = 0                      # Random available port
rate_limit_rps = 10

[postgres]
dsn = ""                      # Set to enable PostgreSQL
analyses_partition_by_depth = true
```

## API Reference

### Authentication
All endpoints require Bearer token authentication:
```bash
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8080/health
```

### Endpoints
- `GET /health` - Server status and feature flags
- `GET /analyse?hash=123&depth=8` - Position analysis
- `POST /tree` - Build tree with GDL program
- `GET /search?q=query` - Search notes with FTS
- `GET /game/{id}` - Retrieve game data

## Performance Targets (v1.1)

With Rust acceleration enabled:
- **Start position NPS**: ≥1.2M nodes/second
- **Overlay probes**: ≤60ms (90th percentile)
- **Exact solver**: ≤16 empties within 120ms
- **Gauntlet throughput**: ≥20 games/min (4 workers, depth 8)

## Training System

### Daily Workflow
1. **Launch trainer**: Access via "Trainer" tab in GUI
2. **Daily queue**: Mix of review items and new positions
3. **Adaptive scheduling**: Leitner boxes (1, 3, 7, 14, 30 days)
4. **Progress tracking**: Success rates by category

### Drill Types
- **Tactics**: Find best move with contextual hints
- **Parity**: Preserve odd-region control
- **Endgame**: Exact solutions under time pressure

## Gauntlet System

### Setup Tournament
```bash
othello-selfplay \
    --profiles elo_400 elo_800 elo_1400 elo_2000 \
    --games 200 \
    --workers 4 \
    --root-noise \
    --output results.json
```

### View Ladder
Results automatically update ratings using Glicko-2. View in GUI "Lab" tab or CLI output.

### Depth Calibration
System automatically maps search depths to ELO ratings with confidence intervals. Only updates when statistical overlap tests pass.

## Troubleshooting

### Rust Acceleration Issues
```bash
# Check if Rust is available
cargo --version

# Rebuild kernel
cd rust_kernel && python build.py

# Test functionality
python -c "import rust_kernel; print('OK')"

# If issues persist, acceleration will auto-disable
```

### Database Migration
```bash
# SQLite to PostgreSQL
python -c "
from othello_coach.db.postgres import PostgresAdapter
adapter = PostgresAdapter('postgresql://...')
adapter.migrate_from_sqlite('~/.othello_coach/coach.sqlite')
"
```

### Performance Issues
- Check `accel_enabled` in config
- Verify Rust kernel installation
- Monitor memory usage with large databases
- Consider PostgreSQL for >1M positions

## Development

### Building from Source
```bash
git clone <repository>
cd othello-coach
python -m venv venv
source venv/bin/activate
pip install -e .

# Run tests
python -m pytest

# With Rust tests
cd rust_kernel && python build.py
python -m pytest tests/test_rust_acceleration.py
```

### Test Suite
- **GDL parser**: Syntax validation and AST serialization
- **Novelty radar**: Shingle generation and similarity
- **Trainer**: Scheduling and drill validation
- **Gauntlet**: Glicko-2 calculations and match simulation
- **Rust parity**: 10k random positions verified

## Architecture

### Core Components
- **Engine**: Search, evaluation, solver (Python + Rust)
- **Insights**: Features, rationales, overlays
- **Trees**: GDL-driven expansion with novelty scoring
- **Trainer**: Spaced repetition with adaptive drills
- **Gauntlet**: Tournament runner with rating calibration
- **API**: Optional REST interface (loopback only)
- **DB**: SQLite (default) or PostgreSQL backend

### Data Flow
1. **Analysis**: Engine → Features → Rationales → UI
2. **Training**: Scheduler → Drill Generator → Validation → Progress
3. **Gauntlets**: Match Generator → Engine Players → Glicko Update → Calibration
4. **Trees**: GDL Parser → Goal Scorer → Novelty Ranker → Export

## License

MIT License - see LICENSE file for details.

## Changelog

### v1.1.0
- Added Rust acceleration kernel
- Implemented GDL authoring system
- Built comprehensive training system
- Added Glicko-2 calibration gauntlets
- Introduced novelty radar
- Optional local API and PostgreSQL support
- Extended solver to ≤16 empties
- Performance improvements and new CLI tools

### v1.0.0
- Initial release with basic analysis and tree building
- SQLite backend with insights and rationales
- PyQt6 GUI with overlay visualization
- Legacy preset-based tree goals
