"""``murmur --uninstall`` removes config, logs, and model caches.

The test redirects every path the uninstaller looks at into a tmp dir
so the user's real ``~/Library/Application Support/Murmur`` and HF
cache are never at risk during CI or local pytest runs.
"""
from __future__ import annotations

import io
from pathlib import Path

from murmur import uninstall


def _seed(tmp_path: Path, monkeypatch) -> dict[str, Path]:
    """Lay down the dirs an uninstall would target. Returns the map of
    role → path so individual tests can assert on each one."""
    config_dir = tmp_path / "config"
    log_dir = tmp_path / "logs"
    hf_root = tmp_path / "hf"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text("backend='local'\n")
    log_dir.mkdir()
    (log_dir / "murmur.log").write_text("hello\n")
    hf_root.mkdir()
    # Two whisper caches + one unrelated model that must NOT be touched.
    for mid in ("base", "small"):
        d = hf_root / f"models--Systran--faster-whisper-{mid}"
        d.mkdir()
        (d / "weights.bin").write_bytes(b"x" * 16)
    (hf_root / "models--unrelated--vendor-thing").mkdir()

    from murmur import _logging as logmod
    from murmur import config as cfgmod
    monkeypatch.setattr(cfgmod, "config_path", lambda: config_dir / "config.toml")
    monkeypatch.setattr(logmod, "log_path", lambda: log_dir / "murmur.log")
    monkeypatch.setenv("HF_HOME", str(hf_root))
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    return {
        "config": config_dir,
        "log": log_dir,
        "hf_root": hf_root,
        "whisper_base": hf_root / "models--Systran--faster-whisper-base",
        "whisper_small": hf_root / "models--Systran--faster-whisper-small",
        "unrelated": hf_root / "models--unrelated--vendor-thing",
    }


def test_collect_targets_finds_config_logs_and_whisper_caches(tmp_path, monkeypatch):
    paths = _seed(tmp_path, monkeypatch)
    targets = uninstall.collect_targets()
    found = {t.path for t in targets}
    assert paths["config"] in found
    assert paths["log"] in found
    assert paths["whisper_base"] in found
    assert paths["whisper_small"] in found


def test_collect_targets_skips_unrelated_models(tmp_path, monkeypatch):
    """A user's other HuggingFace models must not appear in the plan."""
    paths = _seed(tmp_path, monkeypatch)
    target_paths = {t.path for t in uninstall.collect_targets()}
    assert paths["unrelated"] not in target_paths


def test_run_with_yes_removes_everything(tmp_path, monkeypatch):
    paths = _seed(tmp_path, monkeypatch)
    out = io.StringIO()
    rc = uninstall.run(assume_yes=True, out=out)
    assert rc == 0
    assert not paths["config"].exists()
    assert not paths["log"].exists()
    assert not paths["whisper_base"].exists()
    assert not paths["whisper_small"].exists()
    # The unrelated model survived.
    assert paths["unrelated"].exists()


def test_dry_run_changes_nothing(tmp_path, monkeypatch):
    paths = _seed(tmp_path, monkeypatch)
    out = io.StringIO()
    rc = uninstall.run(assume_yes=True, dry_run=True, out=out)
    assert rc == 0
    # All targets still on disk after a dry run.
    for key in ("config", "log", "whisper_base", "whisper_small"):
        assert paths[key].exists(), f"{key} was removed during --dry-run"
    assert "dry-run" in out.getvalue().lower()


def test_run_aborts_on_negative_confirmation(tmp_path, monkeypatch):
    """Pressing 'n' bails before any rmtree."""
    paths = _seed(tmp_path, monkeypatch)
    out = io.StringIO()
    rc = uninstall.run(assume_yes=False, confirm=lambda _p: False, out=out)
    assert rc == 1
    assert paths["config"].exists()
    assert paths["whisper_base"].exists()


def test_run_with_no_state_returns_zero(tmp_path, monkeypatch):
    """Running on a clean machine is a no-op success."""
    from murmur import _logging as logmod
    from murmur import config as cfgmod
    monkeypatch.setattr(cfgmod, "config_path", lambda: tmp_path / "missing/config.toml")
    monkeypatch.setattr(logmod, "log_path", lambda: tmp_path / "missing/log/murmur.log")
    monkeypatch.setenv("HF_HOME", str(tmp_path / "missing"))
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    out = io.StringIO()
    rc = uninstall.run(assume_yes=True, out=out)
    assert rc == 0
    assert "no Murmur state" in out.getvalue()
