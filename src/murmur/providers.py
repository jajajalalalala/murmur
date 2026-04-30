"""Provider and model registry powering the Models page.

A provider is either:
  - ``local`` — a faster-whisper model that runs on the user's machine
    (no key, no network; downloads into Murmur's private model store —
    see ``transcribe.factory.default_local_download_root``).
  - ``openai_compatible`` — a hosted whisper-style endpoint reachable over
    HTTP with the OpenAI Python client (set ``base_url`` to point at the
    vendor; OpenAI itself uses ``base_url=None``).

Adding a new provider/model is a one-file change: append a row to
``LOCAL_MODELS`` or ``CLOUD_PROVIDERS``. The Models page reads the
registry at construction time, so no other code needs to know.

Subscription/OAuth auth is intentionally out of scope (backlog). Each
``CloudProvider`` already carries an ``auth_methods`` tuple so we can add
``"oauth_chatgpt"`` later without restructuring callers.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# ---- Local (on-device) models -------------------------------------------------

@dataclass(frozen=True)
class LocalModel:
    """A faster-whisper model + metadata for the picker UI."""

    id: str            # passed verbatim to faster-whisper.WhisperModel
    label: str
    size_mb: int
    multilingual: bool

    def cache_path(self, download_root: str | os.PathLike[str] | None = None) -> Path:
        """Path faster-whisper writes this model to under ``download_root``.

        Used both to surface a "downloaded" signal in the UI and to drive
        the inline download progress bar. faster-whisper composes the
        per-model directory the same way HuggingFace's hub does:
        ``<root>/models--Systran--faster-whisper-<id>``.

        ``download_root`` is the resolved Murmur-private path (see
        ``transcribe.factory._resolve_local_download_root``). When
        ``None`` we fall back to the legacy HF cache resolution so
        early-boot callers — e.g. the Models page constructing rows
        before a config is plumbed in — still find pre-v0.6 downloads.
        New callers should always pass an explicit root.
        """
        if download_root is not None:
            cache_root = Path(download_root)
        else:
            cache_root = Path(
                os.environ.get("HF_HOME")
                or os.environ.get("HUGGINGFACE_HUB_CACHE")
                or Path.home() / ".cache" / "huggingface" / "hub"
            )
        return cache_root / f"models--Systran--faster-whisper-{self.id}"

    def is_downloaded(self, download_root: str | os.PathLike[str] | None = None) -> bool:
        path = self.cache_path(download_root)
        # Empty dirs (cancelled downloads) shouldn't count as ready.
        return path.is_dir() and any(path.iterdir())


LOCAL_MODELS: tuple[LocalModel, ...] = (
    LocalModel("tiny",             "Tiny",                 75,   True),
    LocalModel("tiny.en",          "Tiny (English)",       75,   False),
    LocalModel("base",             "Base",                 145,  True),
    LocalModel("base.en",          "Base (English)",       145,  False),
    LocalModel("small",            "Small",                466,  True),
    LocalModel("small.en",         "Small (English)",      466,  False),
    LocalModel("medium",           "Medium",               1500, True),
    LocalModel("medium.en",        "Medium (English)",     1500, False),
    LocalModel("large-v3",         "Large v3",             3000, True),
    LocalModel("distil-large-v3",  "Distil Large v3 (EN)", 1500, False),
)


def find_local_model(model_id: str) -> LocalModel | None:
    return next((m for m in LOCAL_MODELS if m.id == model_id), None)


# ---- Cloud (hosted) providers -------------------------------------------------

@dataclass(frozen=True)
class CloudProvider:
    """A hosted Whisper-style endpoint reachable via the OpenAI client."""

    id: str                         # stored in cfg.backend ("openai", "groq", ...)
    label: str
    base_url: str | None            # None = openai.com default
    default_model: str
    models: tuple[str, ...]
    api_key_env: str                # env var the user can drop their key into
    rate_hint: str                  # short string under the model picker
    auth_methods: tuple[str, ...] = ("api_key",)


# Phase 1 ships with one wired-up cloud provider (OpenAI). Phase 2 fills
# the registry with Groq/Kimi/etc — they're just additional rows because
# they all speak the same OpenAI-compatible REST shape.
CLOUD_PROVIDERS: tuple[CloudProvider, ...] = (
    CloudProvider(
        id="openai",
        label="OpenAI Whisper",
        base_url=None,
        default_model="whisper-1",
        models=("whisper-1",),
        api_key_env="OPENAI_API_KEY",
        rate_hint="~$0.006 / minute",
    ),
)


def find_cloud_provider(provider_id: str) -> CloudProvider | None:
    return next((p for p in CLOUD_PROVIDERS if p.id == provider_id), None)
