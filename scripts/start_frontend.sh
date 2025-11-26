#!/usr/bin/env bash
set -e
cd frontend
PORT=8080
if command -v python3 >/dev/null 2>&1; then
  echo "Starting frontend with python3 -m http.server $PORT"
  python3 -m http.server $PORT
elif command -v python >/dev/null 2>&1; then
  echo "Starting frontend with python -m http.server $PORT"
  python -m http.server $PORT
else
  echo "No python found. Install python or use another static server."
  exit 1
fi
