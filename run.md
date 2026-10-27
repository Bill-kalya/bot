# Smoke test (read-only)
python -m scripts.smoke_ccxt

# Shadow mode (paper execution)
$env:SHADOW_MODE="true"; python main.py

# Real demo orders (after shadow verified)
# Edit .env: SHADOW_MODE=false
python main.py

# Tests
python -m pytest tests/ -q

# Lint
python -m ruff check .







# Quick test
python -m scripts.run_experiments --days 1 --windows 1

# Full experiment
python -m scripts.run_experiments --days 30 --windows 5 --accounts 10 100 1000