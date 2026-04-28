"""Wipe Murmur's on-disk state.

Driven by ``murmur --uninstall``. Removes:

* the user config dir (``config.toml`` lives here)
* the log dir (``murmur.log`` and rotated copies)
* every faster-whisper model cache directory under HuggingFace
  (``models--Systran--faster-whisper-*``)

Things this **doesn't** touch — those are user-managed and removing
them automatically would violate the principle of least surprise:

* the ``Murmur.app`` bundle, if installed (``rm -rf /Applications/Murmur.app``)
* the source checkout / virtualenv if running via ``start.sh``
* macOS Privacy & Security entries (Input Monitoring / Accessibility) —
  the OS only lets the user revoke those manually

The uninstall flow lists what it found, asks for confirmation
(unless ``--yes`` was passed), then removes each target. Failures are
reported but don't stop the rest of the cleanup — a partial uninstall
is better than aborting halfway.
"""
from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import _logging as log_mod
from . import config as config_mod


@dataclass(frozen=True)
class Target:
    label: str
    path: Path

    def exists(self) -> bool:
        return self.path.exists()


def _hf_cache_root() -> Path:
    """Mirror the resolution order LocalModel.cache_path uses."""
    return Path(
        os.environ.get("HF_HOME")
        or os.environ.get("HUGGINGFACE_HUB_CACHE")
        or Path.home() / ".cache" / "huggingface" / "hub"
    )


def collect_targets() -> list[Target]:
    """Build the list of paths an uninstall would remove. Pure — no I/O
    other than the existence checks the caller might run."""
    targets: list[Target] = [
        Target("Config", config_mod.config_path().parent),
        Target("Logs", log_mod.log_path().parent),
    ]
    cache_root = _hf_cache_root()
    if cache_root.is_dir():
        for entry in sorted(cache_root.iterdir()):
            name = entry.name
            if name.startswith("models--Systran--faster-whisper-"):
                targets.append(Target(f"Model cache ({name})", entry))
    return targets


def _default_confirm(prompt: str) -> bool:
    """Interactive y/n prompt; defaults to no on Enter."""
    try:
        answer = input(prompt).strip().lower()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def run(
    *,
    assume_yes: bool = False,
    dry_run: bool = False,
    out=sys.stdout,
    confirm: Callable[[str], bool] = _default_confirm,
) -> int:
    """Print plan, optionally confirm, remove. Returns process exit code.

    Tests call this directly with monkey-patched path helpers so no real
    files are touched.
    """
    targets = collect_targets()
    present = [t for t in targets if t.exists()]
    print("Murmur uninstall — the following will be removed:", file=out)
    if not present:
        print("  (nothing — no Murmur state found on disk)", file=out)
        return 0
    for t in present:
        print(f"  • {t.label}: {t.path}", file=out)

    print(file=out)
    print(
        "Manual cleanup (this command can't do these for you):", file=out,
    )
    print(
        "  • /Applications/Murmur.app — drag to Trash if installed",
        file=out,
    )
    print(
        "  • System Settings → Privacy & Security → Input Monitoring "
        "/ Accessibility — revoke the entry for Murmur.app or your "
        "Python binary",
        file=out,
    )

    if dry_run:
        print("\n--dry-run: nothing removed.", file=out)
        return 0

    if not assume_yes:
        print(file=out)
        if not confirm("Proceed with uninstall? [y/N] "):
            print("Aborted.", file=out)
            return 1

    failures: list[tuple[Target, OSError]] = []
    for t in present:
        try:
            shutil.rmtree(t.path)
            print(f"  removed {t.path}", file=out)
        except OSError as exc:
            failures.append((t, exc))
            print(f"  FAILED to remove {t.path}: {exc}", file=out)

    if failures:
        print(
            f"\nUninstall finished with {len(failures)} error(s). "
            "Some files may need to be removed manually.",
            file=out,
        )
        return 2
    print("\nUninstall complete.", file=out)
    return 0


__all__ = ["Target", "collect_targets", "run"]
