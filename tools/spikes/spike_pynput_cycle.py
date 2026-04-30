"""Phase 1 spike: stress-test pynput.keyboard.Listener stop/start cycles.

Throwaway research script feeding GitHub issue #38. Do NOT import from
production code. Run with the project venv:

    /Users/mac/Development/murmur/.venv/bin/python tools/spikes/spike_pynput_cycle.py

The "in-process" workload constructs a fresh Listener, starts it, sleeps,
stops it, sleeps, and repeats 20 times -- mirroring what a hot hotkey
rebind would do. After every cycle we log thread count, surviving thread
names matching pynput|hotkey|murmur, and RSS in MB.

The "subprocess self-test" runs the same workload in a child process and
reports the exit code -- this is the *most important* signal because the
deferral docstring's "unstable" claim is most likely about native
crashes (SIGSEGV / SIGABRT from the CG event tap thread), not Python-level
exceptions.

Verdict heuristic:
  STABLE    if no exceptions, thread count returns to baseline +/- 1,
            RSS growth < 50 MB, AND subprocess exit code == 0.
  UNSTABLE  otherwise, with reason.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import traceback

import psutil
from pynput import keyboard

CYCLES = 20
SLEEP_AFTER_START = 0.5
SLEEP_AFTER_STOP = 0.5
THREAD_NAME_RE = re.compile(r"pynput|hotkey|murmur", re.IGNORECASE)


def rss_mb() -> float:
    return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024


def matching_thread_names() -> list[str]:
    return [t.name for t in threading.enumerate() if THREAD_NAME_RE.search(t.name)]


def run_in_process_workload() -> dict:
    """Run the start/stop cycle in-process; return summary dict."""
    initial_threads = threading.active_count()
    initial_rss = rss_mb()
    print(
        f"[init] active_count={initial_threads} rss={initial_rss:.2f}MB "
        f"matching_threads={matching_thread_names()}"
    )

    exceptions: list[str] = []
    per_cycle: list[dict] = []

    for i in range(1, CYCLES + 1):
        cycle_ok = True
        start_ok = False
        stop_ok = False
        try:
            listener = keyboard.Listener(
                on_press=lambda k: None,
                on_release=lambda k: None,
            )
            listener.start()
            start_ok = True
            time.sleep(SLEEP_AFTER_START)
            listener.stop()
            stop_ok = True
            time.sleep(SLEEP_AFTER_STOP)
        except Exception as exc:  # noqa: BLE001 - we want to capture anything
            cycle_ok = False
            tb = traceback.format_exc()
            exceptions.append(f"cycle {i}: {exc!r}\n{tb}")

        record = {
            "cycle": i,
            "active_count": threading.active_count(),
            "matching_threads": matching_thread_names(),
            "rss_mb": rss_mb(),
            "start_ok": start_ok,
            "stop_ok": stop_ok,
            "ok": cycle_ok,
        }
        per_cycle.append(record)
        print(
            f"[cycle {i:02d}] active_count={record['active_count']} "
            f"rss={record['rss_mb']:.2f}MB start_ok={start_ok} stop_ok={stop_ok} "
            f"matching={record['matching_threads']}"
        )

    final_threads = threading.active_count()
    final_rss = rss_mb()
    all_threads = [t.name for t in threading.enumerate()]

    print()
    print(f"[final] active_count={final_threads} rss={final_rss:.2f}MB")
    print(f"[final] all_threads={all_threads}")
    print(
        f"[final] delta active_count={final_threads - initial_threads} "
        f"delta_rss={final_rss - initial_rss:.2f}MB"
    )
    print(f"[final] exceptions raised: {len(exceptions)}")
    for e in exceptions:
        print(e)

    return {
        "initial_threads": initial_threads,
        "initial_rss": initial_rss,
        "final_threads": final_threads,
        "final_rss": final_rss,
        "exceptions": exceptions,
        "per_cycle": per_cycle,
        "all_threads": all_threads,
    }


def in_process_verdict(summary: dict) -> tuple[str, str]:
    if summary["exceptions"]:
        return "UNSTABLE", f"{len(summary['exceptions'])} exception(s) raised"
    delta_threads = summary["final_threads"] - summary["initial_threads"]
    if abs(delta_threads) > 1:
        return (
            "UNSTABLE",
            f"thread count drifted by {delta_threads} (>1) "
            f"from {summary['initial_threads']} to {summary['final_threads']}",
        )
    delta_rss = summary["final_rss"] - summary["initial_rss"]
    if delta_rss > 50:
        return "UNSTABLE", f"RSS grew by {delta_rss:.2f} MB (>50)"
    return "STABLE", (
        f"thread delta={delta_threads}, rss delta={delta_rss:.2f}MB, "
        "no exceptions"
    )


SUBPROCESS_TAG = "__pynput_cycle_child__"


def run_subprocess_self_test() -> dict:
    """Re-exec self in a child process and capture exit code + output."""
    print()
    print("=" * 60)
    print("subprocess self-test (catches SIGSEGV / SIGABRT)")
    print("=" * 60)
    proc = subprocess.run(
        [sys.executable, __file__, SUBPROCESS_TAG],
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(f"[subprocess] exit_code={proc.returncode}")
    print(f"[subprocess] stdout (last 30 lines):")
    for line in proc.stdout.splitlines()[-30:]:
        print(f"  {line}")
    if proc.stderr.strip():
        print(f"[subprocess] stderr:")
        for line in proc.stderr.splitlines()[-30:]:
            print(f"  {line}")
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == SUBPROCESS_TAG:
        # Child: just run the in-process workload and exit.
        # If pynput segfaults, the parent will see a non-zero exit code.
        run_in_process_workload()
        return 0

    print(f"python: {sys.version}")
    import platform

    print(f"macOS: {platform.mac_ver()}")
    try:
        from importlib.metadata import version as _pkg_version

        print(f"pynput: {_pkg_version('pynput')}")
    except Exception as exc:  # noqa: BLE001
        print(f"pynput: <unknown> ({exc!r})")
    print()

    summary = run_in_process_workload()
    in_proc_status, in_proc_reason = in_process_verdict(summary)

    sub = run_subprocess_self_test()
    sub_status = "STABLE" if sub["exit_code"] == 0 else "UNSTABLE"
    sub_reason = (
        "exit_code=0"
        if sub["exit_code"] == 0
        else f"non-zero exit_code={sub['exit_code']} (negative => signal)"
    )

    print()
    print("=" * 60)
    print(f"VERDICT (in-process):  {in_proc_status} -- {in_proc_reason}")
    print(f"VERDICT (subprocess):  {sub_status} -- {sub_reason}")
    overall = (
        "STABLE"
        if in_proc_status == "STABLE" and sub_status == "STABLE"
        else "UNSTABLE"
    )
    print(f"VERDICT (overall):     {overall}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
