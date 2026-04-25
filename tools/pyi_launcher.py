"""PyInstaller entrypoint for the Murmur.app bundle.

PyInstaller turns whatever script you hand it into a top-level `__main__`,
which breaks relative imports inside our package. So instead of pointing
PyInstaller at `src/murmur/__main__.py`, we point it here — this file
imports the package the normal way and dispatches to `main()`.

Bonus: when launched as a `.app` from Finder, stdout/stderr point at /dev/null
or the system log with no easy way to see them. We re-bind them to a file in
~/Library/Logs/Murmur/ so anything that bypasses our logger (Qt warnings,
pynput's own prints, third-party native tracebacks) is still captured.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _redirect_streams_when_bundled() -> None:
    """In a PyInstaller .app bundle, send stdout/stderr to a log file."""
    if not getattr(sys, "frozen", False):
        return
    log_dir = Path.home() / "Library" / "Logs" / "Murmur"
    log_dir.mkdir(parents=True, exist_ok=True)
    raw = log_dir / "murmur.stderr.log"
    # Line-buffered so `tail -f` shows things promptly. Intentionally never
    # closed — these streams need to outlive the function for the rest of
    # the process.
    f = open(raw, "a", buffering=1, encoding="utf-8", errors="replace")  # noqa: SIM115
    sys.stdout = f
    sys.stderr = f
    os.environ.setdefault("PYTHONUNBUFFERED", "1")


_redirect_streams_when_bundled()

from murmur.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
