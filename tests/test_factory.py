"""``transcribe.factory`` resolves the local-model download_root.

Issue #12 moved Murmur's model store from the shared HuggingFace cache
to a Murmur-private path under ``platformdirs.user_data_dir``. The
factory is the one place that materialises the empty-string default
into a real directory, so we exercise the resolution + on-demand
``mkdir`` behaviour here.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from platformdirs import user_data_dir

from murmur import config as config_mod
from murmur.transcribe.factory import (
    _resolve_local_download_root,
    default_local_download_root,
)


def test_default_path_matches_platformdirs():
    """The default lives under ``user_data_dir("Murmur") / "models"``."""
    expected = Path(user_data_dir("Murmur")) / "models"
    assert default_local_download_root() == expected


def test_resolve_returns_platformdirs_path_when_config_empty(tmp_path, monkeypatch):
    """Empty-string default → fall back to platformdirs."""
    fake = tmp_path / "data" / "Murmur" / "models"
    monkeypatch.setattr(
        "murmur.transcribe.factory.default_local_download_root",
        lambda: fake,
    )
    cfg = config_mod.Config(local=config_mod.LocalBackendConfig(download_root=""))
    resolved = _resolve_local_download_root(cfg)
    assert Path(resolved) == fake
    # mkdir-on-demand: the directory exists after resolve even though
    # nothing created it ahead of time.
    assert fake.exists()


def test_resolve_creates_missing_directory(tmp_path, monkeypatch):
    """The platformdirs path is created on first resolve."""
    fake = tmp_path / "deep" / "nested" / "models"
    assert not fake.exists()
    monkeypatch.setattr(
        "murmur.transcribe.factory.default_local_download_root",
        lambda: fake,
    )
    cfg = config_mod.Config(local=config_mod.LocalBackendConfig(download_root=""))
    _resolve_local_download_root(cfg)
    assert fake.is_dir()


def test_resolve_returns_configured_path_when_non_empty(tmp_path):
    """Non-empty config wins — power users can point Murmur elsewhere."""
    target = tmp_path / "elsewhere"
    cfg = config_mod.Config(
        local=config_mod.LocalBackendConfig(download_root=str(target)),
    )
    resolved = _resolve_local_download_root(cfg)
    assert Path(resolved) == target
    assert target.is_dir()


def test_resolve_strips_whitespace(tmp_path):
    """Defensive: a TOML field with leading/trailing space still resolves."""
    target = tmp_path / "spaced"
    cfg = config_mod.Config(
        local=config_mod.LocalBackendConfig(download_root=f"  {target}  "),
    )
    resolved = _resolve_local_download_root(cfg)
    assert Path(resolved) == target


def test_local_backend_config_default_download_root_is_empty():
    """The default is the empty string — TOML migration not required."""
    assert config_mod.LocalBackendConfig().download_root == ""


def test_config_save_load_preserves_download_root(tmp_path, monkeypatch):
    """The new field round-trips through the TOML file."""
    monkeypatch.setattr(
        config_mod, "config_path", lambda: tmp_path / "config.toml",
    )
    cfg = config_mod.load()
    cfg.local.download_root = str(tmp_path / "custom-store")
    config_mod.save(cfg)
    reloaded = config_mod.load()
    assert reloaded.local.download_root == str(tmp_path / "custom-store")


def test_build_local_passes_download_root(tmp_path, monkeypatch):
    """``build()`` plumbs the resolved root into ``LocalWhisper``."""
    target = tmp_path / "store"
    cfg = config_mod.Config(
        backend="local",
        local=config_mod.LocalBackendConfig(
            model="base",
            download_root=str(target),
        ),
    )
    from murmur.transcribe import factory as factory_mod

    transcriber = factory_mod.build(cfg)
    assert transcriber.download_root == str(target)
    assert target.is_dir()


def test_build_local_empty_download_root_uses_platformdirs(tmp_path, monkeypatch):
    fake = tmp_path / "data" / "Murmur" / "models"
    monkeypatch.setattr(
        "murmur.transcribe.factory.default_local_download_root",
        lambda: fake,
    )
    cfg = config_mod.Config(
        backend="local",
        local=config_mod.LocalBackendConfig(model="base"),
    )
    from murmur.transcribe import factory as factory_mod

    transcriber = factory_mod.build(cfg)
    assert Path(transcriber.download_root) == fake


def test_build_still_refuses_empty_model():
    cfg = config_mod.Config(
        backend="local",
        local=config_mod.LocalBackendConfig(model=""),
    )
    from murmur.transcribe import factory as factory_mod

    with pytest.raises(RuntimeError, match="No local model selected"):
        factory_mod.build(cfg)
