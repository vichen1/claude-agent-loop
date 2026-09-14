#!/usr/bin/env bash
python - << 'PY'
import sys
from chunker import chunk

cases = [
    (([1,2,3,4,5], 2), [[1,2],[3,4],[5]]),
    (([1,2,3,4], 2),   [[1,2],[3,4]]),
    (([1], 3),         [[1]]),
    (([], 2),          []),
]
for args, expected in cases:
    if chunk(*args) != expected:
        sys.exit(1)
sys.exit(0)
PY
