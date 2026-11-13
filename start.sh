#!/bin/sh
DIRECTORY=$(dirname "$0")
export DISPLAY=:0
cd "$DIRECTORY" || exit 1

LOG_DIR="/var/log/JbClock"
LOG_FILE="${LOG_DIR}/logs.log"

mkdir -p "$LOG_DIR"

PYTHON_BIN=".venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

while true
do
    "$PYTHON_BIN" main.py >>"$LOG_FILE" 2>&1
    sleep 1
done
