#!/usr/bin/env python3
"""sessionStart: Brain (doubt_by_design2.md) leads; Body witnesses in parallel."""
from __future__ import annotations

import json
import sys

# No engine observe here — Brain already holds doubt_by_design2.md; Body runs ∥ collapse.


def main() -> None:
    sys.stdout.write("{}")
    sys.stdout.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        sys.stderr.write(f"session_start hook error: {exc}\n")
        sys.stdout.write("{}")
        sys.stdout.flush()
