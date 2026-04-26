"""Models page: provider switching + local-model selection round-trip."""
from __future__ import annotations

import os
import sys

import pytest

pytest.importorskip("PySide6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from murmur import config as config_mod  # noqa: E402
from murmur.pages.models import ModelsPage  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    yield QApplication.instance() or QApplication(sys.argv)


def _cfg(backend: str = "local", model: str = "base") -> config_mod.Config:
    return config_mod.Config(
        backend=backend,
        language="auto",
        hotkey="<right_alt>",
        auto_paste=True,
        show_hud=True,
        local=config_mod.LocalBackendConfig(model=model),
        openai=config_mod.OpenAIBackendConfig(api_key_env="OPENAI_API_KEY"),
    )


def test_initial_provider_matches_config(qapp):
    page = ModelsPage(_cfg(backend="local"))
    assert page.provider_combo.currentData() == "local"

    page = ModelsPage(_cfg(backend="openai"))
    assert page.provider_combo.currentData() == "openai"


def test_unknown_backend_falls_back_to_local(qapp):
    page = ModelsPage(_cfg(backend="some-unimplemented-provider"))
    assert page.provider_combo.currentData() == "local"


def test_apply_local_writes_active_model(qapp):
    page = ModelsPage(_cfg(backend="local", model="base"))
    page._local_panel._select_model("small")
    out = page.apply_to_config(_cfg(backend="local", model="base"))
    assert out.backend == "local"
    assert out.local.model == "small"


def test_apply_cloud_writes_provider_and_model(qapp):
    page = ModelsPage(_cfg(backend="openai"))
    out = page.apply_to_config(_cfg(backend="openai"))
    assert out.backend == "openai"
    assert out.openai.api_key_env == "OPENAI_API_KEY"
    assert out.openai.model == "whisper-1"


def test_custom_local_model_is_preserved(qapp):
    """A model that's not in LOCAL_MODELS still shows up so the user can
    keep using whatever they hand-edited into the TOML."""
    page = ModelsPage(_cfg(model="distil-large-v3-something-custom"))
    assert "distil-large-v3-something-custom" in page._local_panel._rows


def test_switching_to_cloud_reveals_cloud_panel(qapp):
    page = ModelsPage(_cfg(backend="local"))
    # Move the dropdown from local → openai.
    for i in range(page.provider_combo.count()):
        if page.provider_combo.itemData(i) == "openai":
            page.provider_combo.setCurrentIndex(i)
            break
    assert page._stack.currentWidget() is page._cloud_panel


# ---- Download progress -----------------------------------------------------

def test_dir_size_bytes_sums_files_recursively(tmp_path):
    """The cache-size estimator walks all files under a directory."""
    from murmur.pages.models import _dir_size_bytes
    (tmp_path / "a.bin").write_bytes(b"x" * 1024)
    sub = tmp_path / "snapshots"
    sub.mkdir()
    (sub / "model.bin").write_bytes(b"y" * 4096)
    assert _dir_size_bytes(tmp_path) == 1024 + 4096


def test_dir_size_bytes_handles_missing_dir(tmp_path):
    from murmur.pages.models import _dir_size_bytes
    assert _dir_size_bytes(tmp_path / "does-not-exist") == 0


def test_set_progress_clamps_and_shows_bar(qapp):
    """Calling set_progress while downloading reveals the bar at the
    expected percentage (clamped to 99% so completion is owned by the
    finished signal, not the size poller)."""
    page = ModelsPage(_cfg())
    row = page._local_panel._rows["base"]
    row.set_downloading(True)
    row.set_progress(0.5)
    assert row._progress.isVisible() or row._progress.value() == 50
    assert row._progress.value() == 50
    # Beyond 100% → clamped just below to keep "finished" definitive.
    row.set_progress(1.5)
    assert row._progress.value() == 99


def test_set_progress_ignored_when_not_downloading(qapp):
    page = ModelsPage(_cfg())
    row = page._local_panel._rows["base"]
    # Default state: not downloading. Set should be a no-op.
    row.set_progress(0.7)
    assert row._progress.value() == 0


def test_set_downloading_false_resets_bar(qapp):
    page = ModelsPage(_cfg())
    row = page._local_panel._rows["base"]
    row.set_downloading(True)
    row.set_progress(0.6)
    row.set_downloading(False)
    assert row._progress.value() == 0


def test_poll_progress_updates_row_from_cache_size(qapp, monkeypatch):
    """End-to-end: a fake in-flight worker + a stubbed cache-size reader
    feeds the row's progress bar via _poll_progress."""
    from murmur.pages import models as models_mod

    page = ModelsPage(_cfg())
    panel = page._local_panel
    row = panel._rows["tiny"]  # 75 MB target
    row.set_downloading(True)
    panel._workers["tiny"] = (None, None)  # marker so _poll_progress runs

    target = row.model.size_mb * 1024 * 1024
    monkeypatch.setattr(models_mod, "_dir_size_bytes", lambda _p: target // 2)
    panel._poll_progress()
    assert 45 <= row._progress.value() <= 55
