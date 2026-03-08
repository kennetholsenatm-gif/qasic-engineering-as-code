"""Allow python -m pulse to run the compile CLI."""
from __future__ import annotations

from .compile_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
