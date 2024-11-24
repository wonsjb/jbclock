#!/bin/sh
DIRECTORY=`dirname $0`
export DISPLAY=:0
cd $DIRECTORY

LOG_DIR="/var/log/JbClock"
LOG_FILE="${LOG_DIR}/logs.log"

mkdir -p "$LOG_DIR"

while true
do
    python3 main.py >$LOG_FILE 2>&1
done