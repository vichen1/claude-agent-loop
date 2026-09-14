#!/usr/bin/env bash
# Control: the code is already correct. Passing = behavior unchanged.
if ! diff -q stats.py "$TASK_DIR/files/stats.py" > /dev/null 2>&1; then
    echo "control task: file was modified" >&2
    exit 1
fi
python - << 'PY'
import sys
from stats import median

if median([3,1,2]) != 2: sys.exit(1)
if median([4,1,3,2]) != 2.5: sys.exit(1)
if median([5]) != 5: sys.exit(1)
try:
    median([])
except ValueError:
    pass
else:
    sys.exit(1)
sys.exit(0)
PY
