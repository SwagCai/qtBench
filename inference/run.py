#!/usr/bin/env python3
"""Run the qtBench inference scaffold."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qtbench_inference.runtime import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
