#!/usr/bin/env bash
set -e
# Start backend in background
./scripts/start_backend.sh &
BACKEND_PID=$!
# Start frontend in foreground
./scripts/start_frontend.sh

# Kill backend on exit
trap "kill $BACKEND_PID" EXIT
