#!/bin/bash
# One-click launcher: sets up a virtual environment on first run, then starts the dashboard.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/streamlit ]; then
  echo "First run — installing dependencies…"
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
(sleep 4 && open http://localhost:8501) &
.venv/bin/streamlit run app.py --server.headless true
