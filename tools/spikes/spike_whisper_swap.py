"""Phase 1 spike: stress-test faster-whisper model swap (tiny <-> base).

Throwaway research script feeding GitHub issue #38. Do NOT import from
production code. Run with the project venv:

    /Users/mac/Development/murmur/.venv/bin/python tools/spikes/spike_whisper_swap.py

We construct a WhisperModel, transcribe one second of silence, del + gc,
then construct the *other* model, transcribe, del + gc. Repeat 5 times.
After each swap we log RSS and the number of open file descriptors.

If neither model is cached locally we skip the script (the spike is
about hot-reload safety, not download behaviour).

Verdict heuristic:
  STABLE   if RSS growth < 200 MB and FD count is bounded (<= initial+10).
  UNSTABLE otherwise, with reason.
"""

from __future__ import annotations

import gc
import os
import sys
import time
from pathlib import Path

import numpy as np
import psutil

SWAPS = 5
# Pair of models to alternate. We prefer ("tiny", "base") but fall back to
# ("tiny.en", "base") if the multilingual tiny isn't cached -- the spike
# is about swap mechanics, not language coverage.
PREFERRED_MODELS = ["tiny", "base"]
FALLBACK_MODELS = ["tiny.en", "base"]


def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


def fd_count() -> int:
    try:
        return len(psutil.Process(os.getpid()).open_files())
    except Exception:
        return -1


def _resolve_local_download_root() -> str | None:
    """Mirror the production resolution for download_root, but read-only.

    Reads ~/Library/Application Support/Murmur/config.toml if present;
    falls back to None (let faster-whisper / HF use the default cache).
    """
    cfg = Path.home() / "Library/Application Support/Murmur/config.toml"
    if cfg.exists():
        try:
            import tomllib

            with cfg.open("rb") as f:
                data = tomllib.load(f)
            root = data.get("local", {}).get("download_root", "") or ""
            if root:
                return root
        except Exception:
            pass
    # Murmur defaults to platformdirs user_cache_dir/Murmur/models.
    default = Path.home() / "Library/Application Support/Murmur/models"
    return str(default) if default.exists() else None


def _hf_repo_dir(download_root: str | None, name: str) -> Path | None:
    if download_root is None:
        return None
    p = Path(download_root) / f"models--Systran--faster-whisper-{name}"
    return p if p.exists() else None


def models_cached(download_root: str | None, names: list[str]) -> dict[str, bool]:
    """Return {name: cached} for each model in names."""
    out = {}
    for name in names:
        d = _hf_repo_dir(download_root, name)
        out[name] = d is not None
    return out


def pick_models(download_root: str | None) -> tuple[list[str] | None, dict]:
    """Pick a usable pair of cached models, or return (None, status)."""
    pref = models_cached(download_root, PREFERRED_MODELS)
    if all(pref.values()):
        return PREFERRED_MODELS, {"chosen": PREFERRED_MODELS, "preferred": pref}
    fb = models_cached(download_root, FALLBACK_MODELS)
    if all(fb.values()):
        return FALLBACK_MODELS, {
            "chosen": FALLBACK_MODELS,
            "preferred": pref,
            "fallback": fb,
            "note": "tiny multilingual not cached; using tiny.en for swap pair",
        }
    return None, {"preferred": pref, "fallback": fb}


def main() -> int:
    print(f"python: {sys.version}")
    import platform

    print(f"macOS: {platform.mac_ver()}")
    import faster_whisper

    print(f"faster_whisper: {faster_whisper.__version__}")

    download_root = _resolve_local_download_root()
    print(f"download_root: {download_root}")
    models, status = pick_models(download_root)
    print(f"model selection: {status}")

    if models is None:
        print()
        print("=" * 60)
        print(
            "VERDICT: SKIPPED -- models not cached locally; "
            "run after manual download via Models page."
        )
        print("=" * 60)
        return 0
    print(f"swap pair: {models}")

    from faster_whisper import WhisperModel

    silence = np.zeros(16000, dtype=np.float32)
    initial_rss = rss_mb()
    initial_fd = fd_count()
    print(f"[init] rss={initial_rss:.2f}MB open_files={initial_fd}")

    per_swap: list[dict] = []

    for i in range(1, SWAPS + 1):
        for name in models:
            t0 = time.time()
            model = WhisperModel(
                name,
                device="auto",
                compute_type="int8",
                download_root=download_root,
            )
            kwargs = {} if name.endswith(".en") else {"language": "en"}
            segments, _info = model.transcribe(silence, **kwargs)
            # force generator drain so we exercise the real path
            _segs = list(segments)
            del model
            gc.collect()
            dt = time.time() - t0
            r = rss_mb()
            f = fd_count()
            print(
                f"[swap {i}/{SWAPS} model={name:>4s}] "
                f"rss={r:.2f}MB open_files={f} elapsed={dt:.2f}s segs={len(_segs)}"
            )
            per_swap.append({"swap": i, "model": name, "rss": r, "fd": f})

    final_rss = rss_mb()
    final_fd = fd_count()
    delta_rss = final_rss - initial_rss
    delta_fd = final_fd - initial_fd
    print()
    print(f"[final] rss={final_rss:.2f}MB open_files={final_fd}")
    print(f"[final] delta_rss={delta_rss:.2f}MB delta_fd={delta_fd}")

    reasons = []
    if delta_rss > 200:
        reasons.append(f"RSS grew by {delta_rss:.2f} MB (>200)")
    if final_fd > initial_fd + 10:
        reasons.append(f"FD count grew by {delta_fd} (>10)")
    status = "STABLE" if not reasons else "UNSTABLE"
    print()
    print("=" * 60)
    if status == "STABLE":
        print(
            f"VERDICT: STABLE -- delta_rss={delta_rss:.2f}MB, delta_fd={delta_fd}"
        )
    else:
        print(f"VERDICT: UNSTABLE -- {'; '.join(reasons)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
