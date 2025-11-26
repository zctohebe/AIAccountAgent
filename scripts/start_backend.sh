#!/usr/bin/env bash
set -e
echo "Installing Python requirements..."
python3 -m pip install -r backend/requirements.txt

echo "Starting backend dev server on http://0.0.0.0:8000"
python3 backend/handler.py
