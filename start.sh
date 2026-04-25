#!/usr/bin/env bash
# Start bashupload server.
# Usage: ./start.sh [port]
set -eu
cd "$(dirname "$0")"
PORT="${1:-16261}"
exec python3 server.py "$PORT"
