#!/usr/bin/env bash
python - << 'PY'
import sys
from utils import calculate_average

if calculate_average([1, 2, 3]) != 2.0:
    sys.exit(1)

try:
    r = calculate_average([])
except ValueError:
    sys.exit(0)
except Exception:
    sys.exit(1)
sys.exit(0 if r == 0 else 1)
PY
