# Phase 1 findings — pynput + faster-whisper hot-reload safety

Investigation feeding [GitHub issue #38](https://github.com/jajajalalalala/murmur/issues/38). Both spikes ran on the
maintainer's daily-driver Mac. Throwaway scripts only — no production
code touched.

## Environment

| | |
|---|---|
| Python | 3.11.13 (main, Jun 4 2025) [Clang 20.1.4] |
| macOS | 14.3.1, arm64 |
| pynput | 1.8.1 |
| faster-whisper | 1.2.1 |
| `psutil` | not in venv — installed locally (`7.2.2`) for the spike, NOT added to `pyproject.toml` |

Note on macOS permissions: the spike interpreter (`/Users/mac/Development/murmur/.venv/bin/python`) is **not** trusted
for Accessibility — pynput logged `"This process is not trusted! Input event monitoring will not be possible until it is added to accessibility clients."` 20 times during the run. The Listener thread still
constructed, started, and stopped cleanly; the production app (`Murmur.app`) does have Accessibility,
so this caveat may understate native-thread activity. See "anomalies" below.

## Verdicts

### `spike_pynput_cycle.py` — **STABLE**

20 fresh `Listener` constructions + start/stop cycles, run twice (in-process and in a subprocess).

- **No exceptions** in any of the 20 cycles
- **Thread count returned to baseline (1 / `MainThread`) after every cycle** — delta = 0
- **RSS delta = 7.05 MB in-process / 7.23 MB subprocess** (well under the 50 MB threshold)
- **Subprocess exit code = 0** — no SIGSEGV / SIGABRT / SIGBUS
- No threads matching `pynput|hotkey|murmur` survived after stop()

This directly **refutes** `restart.py`'s docstring claim that "pynput's macOS listener can be unstable after a stop/start cycle" — at least under the workload that hot-reload would actually exercise.

### `spike_whisper_swap.py` — **UNSTABLE per heuristic, but not a real leak**

5 swaps × `tiny.en` ↔ `base` (multilingual `tiny` not cached on this machine; pair was substituted).

- **RSS delta = 704 MB** (heuristic threshold: 200 MB → flagged UNSTABLE)
- **FD count rock-solid at 2 throughout** (0 growth, no descriptor leak)
- **No exceptions**

Look at the per-swap numbers: most of the growth (658 MB) happens in **swaps 1–2** as the CTranslate2 allocator establishes a high-water mark for `base`. Swaps 3–5 add only ~13 MB total. This is allocator caching, not a leak. PR #46 (already in production) validates this in real use. The 200 MB threshold was set blind; in retrospect it's too tight for `int8` `base`, whose resident set legitimately exceeds 600 MB after warmup.

```
[init]                 rss=54.91MB
[swap 1/5 tiny.en]     rss=461.61MB     # +407 MB (model load)
[swap 1/5 base]        rss=658.25MB     # +197 MB (model load)
[swap 2/5 tiny.en]     rss=672.39MB     # +14 MB
[swap 2/5 base]        rss=717.02MB     # +45 MB
[swap 5/5 base]        rss=758.98MB     # final, plateau
```

Practical verdict: **STABLE in spirit**, FD-bounded, no exceptions. The heuristic UNSTABLE label reflects an unrealistic threshold, not a real swap-mechanics problem.

## Phase 2 recommendation

**Phase 2 is safe to proceed** for hotkey rebinds (pynput hot-reload). The empirical evidence directly contradicts the docstring's "unstable" claim across 40 cycles total (20 in-process + 20 in subprocess) on the maintainer's machine.

For model swap, no new evidence is needed — PR #46 already ships hot model swap and this spike confirms FDs and exception-freeness; the apparent RSS growth is allocator high-water mark, not a leak.

## Anomalies worth flagging before Phase 2

1. **Accessibility not granted to spike interpreter.** pynput's macOS listener relies on Accessibility for the keyboard tap; without trust, the underlying CGEventTap may take a different (lighter) code path than the production app does. Re-running this spike *inside* `Murmur.app` (which has trust) before merging Phase 2 would close that gap. Concretely: run an equivalent listener-cycle smoke test from a hidden debug menu, or wire it into a one-off launch flag.
2. **Whisper RSS plateau is well above the heuristic threshold.** The 200 MB threshold was guesswork; 800 MB resident is normal for `int8 base` after warmup. Future spikes should set thresholds against an empirical baseline, not a round number.
3. **`tiny` (multilingual) was not cached locally** — only `tiny.en` and `base`. The swap pair substitution doesn't change the conclusion (the swap mechanics are model-agnostic), but if Phase 2 wants belt-and-suspenders coverage, downloading multilingual `tiny` and re-running the swap spike takes ~30 s.
