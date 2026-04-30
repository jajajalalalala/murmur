# Contributing to Murmur

Murmur is a personal tool, but it follows a real engineering workflow so that anyone (human or AI agent) can pick it up months from now and ship a change without breaking anything.

## TL;DR

```
main is protected. Every change goes through:
  branch → commits → push → PR → green CI → squash-merge → delete branch
```

## Setup

Murmur uses [uv](https://github.com/astral-sh/uv) for Python and dependency management. You don't need a system Python — `start.sh` installs uv (if missing), pins Python via `.python-version`, creates `.venv/`, and installs everything.

```bash
git clone https://github.com/jajajalalalala/murmur.git
cd murmur
./start.sh                   # default: launches the menu-bar tray app
./start.sh --cli             # CLI mode (Enter to start/stop)
./start.sh --setup-only      # install dependencies, don't launch
./start.sh --reset           # wipe .venv and reinstall
```

The first run downloads a Whisper model (~150 MB for `base`).

### Show / inspect config

The runtime config lives in a TOML file under `~/Library/Application Support/Murmur/` on macOS. To print its location and current contents:

```bash
.venv/bin/python -m murmur --show-config
```

Power users can hand-edit the `hotkey` field directly using [pynput hotkey syntax](https://pynput.readthedocs.io/en/latest/keyboard.html#monitoring-the-keyboard) — e.g. `<f9>`, `<ctrl>+<shift>+<space>`, `<fn>`. The Shortcuts page in the main window covers everything you can reasonably bind, so reach for the TOML only if you're scripting something.

### macOS permissions during dev

Murmur needs **Microphone** and **Input Monitoring** on macOS. Both attach to whichever binary runs the listener:

- Launching via `./start.sh` → the grant attaches to `.venv/bin/python` (or your terminal app, depending on macOS version). It can break when the venv is recreated — re-grant in System Settings if so.
- Launching `dist/Murmur.app` (see "Build" below) → the grant attaches to the bundle and survives rebuilds. **Recommended for daily use.**

After flipping a permission ON, **quit and relaunch** Murmur — macOS only re-checks at process start.

## Build a standalone `Murmur.app`

```bash
./build.sh                   # produces dist/Murmur.app
./build.sh --clean           # wipe dist/ and build/ first
open dist/Murmur.app         # or drag into /Applications
```

The build:
- Bundles Python + all dependencies via PyInstaller — the app runs without any system Python.
- Generates and embeds the Murmur icon.
- Sets `LSUIElement=true` so Murmur lives only in the menu bar (no Dock icon).
- Adds the macOS permission strings so the system prompts are human-readable.
- **Ad-hoc-codesigns** the bundle so Gatekeeper allows it on your machine.

Tagged releases (`v*`) are built by the [Release workflow](.github/workflows/release.yml) on a `macos-14` runner, wrapped in a `.dmg` via `hdiutil`, and attached to the GitHub Release.

> **Codesigning note:** v1.0 ships ad-hoc-signed only. A real Developer ID + notarization workflow is on the v1.1+ backlog ([ROADMAP.md](ROADMAP.md)). Until then, first-launch users have to right-click → Open.

> **Windows:** packaging support is on the roadmap. For now, run via `./start.sh` on Windows under WSL or Git Bash.

## Workflow

### 1. Start from a clean main

```bash
git checkout main
git pull --ff-only
```

### 2. Create a topic branch

Name it by intent:

| Prefix       | Use for                              | Example                            |
|--------------|--------------------------------------|------------------------------------|
| `feat/`      | New user-visible feature             | `feat/auto-paste`                  |
| `fix/`       | Bug fix                              | `fix/start-sh-venv-mismatch`       |
| `chore/`     | Tooling, CI, deps, repo plumbing     | `chore/contributor-workflow`       |
| `docs/`      | Documentation only                   | `docs/macos-permissions`           |
| `refactor/`  | Internal change, no behavior change  | `refactor/extract-state-machine`   |

```bash
git checkout -b feat/my-thing
```

### 3. Commit in small, reviewable steps

- Imperative subject line under 70 chars: `feat: add waveform indicator to tray icon`.
- One logical change per commit when possible.
- If you are fixing a typo or formatting in your own PR before merge, use `--amend` or `--fixup`.

### 4. Run the local checks before pushing

These mirror what CI does. Don't push until they pass.

```bash
./start.sh --setup-only            # confirms install still works end-to-end
.venv/bin/pytest -q                # unit tests
.venv/bin/ruff check src tests     # lint
```

### 5. Push and open a PR

```bash
git push -u origin feat/my-thing
```

Then open a PR against `main`. The [PR template](.github/PULL_REQUEST_TEMPLATE.md) will pre-fill the description — fill in every section.

### 6. Wait for CI, then merge

- Required: the **CI** workflow must be green.
- Use **squash and merge**. The PR title becomes the commit message on `main`, so make it good.
- Delete the branch after merge.

### 7. Update the roadmap *in the same PR*

If your change ticks a checkbox in [ROADMAP.md](ROADMAP.md), tick it. If it adds scope, add a checkbox. The roadmap is the living spec.

## What to test

- **Unit-testable things** (config, state machine, audio buffer math): cover with `pytest`.
- **Hardware/permission things** (mic capture, global hotkeys, paste): smoke-test manually on macOS and document in the PR description what you tried.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for module layout and data flow, and `docs/adr/` for the locked-in design decisions (provider registry, single OpenAI-compatible transcriber, API-key storage, etc.).

## Code style

- Python 3.10+ syntax (we pin 3.11 at runtime, but support 3.10 for type-hint use).
- `ruff` enforces formatting and lint. Run `ruff check --fix` before committing.
- No trailing whitespace, no debug prints in committed code.
- Prefer explicit imports over `*`.
- Public modules go in `src/murmur/`, tests in `tests/`. Mirror the source path.

## Dependencies

Adding a runtime dependency is a real cost (install time, install failures, audit surface). Only add one when:

1. There is no reasonable stdlib path.
2. The library is actively maintained.
3. You document *why* in the PR description.

Pin in `pyproject.toml` with a sensible lower bound; do not pin upper bounds unless a known breaking change forces it.

## Reporting bugs

Open an issue with:

- macOS / Windows version
- Python version (`.venv/bin/python --version`)
- Output of `python -m murmur --show-config`
- Steps to reproduce, expected vs. actual
- Relevant log excerpts from `~/Library/Logs/Murmur/murmur.log`

## Uninstalling (during dev)

```bash
.venv/bin/python -m murmur --uninstall --dry-run   # preview
.venv/bin/python -m murmur --uninstall --yes       # actually remove
```

Wipes config, logs, and downloaded Whisper models. The bundled `Murmur.app` and macOS Privacy & Security entries are listed in the printed plan but not deleted automatically — drag the app to the Trash and revoke the toggles manually.

## License

By contributing you agree that your contributions are licensed under the MIT License covering this repo.
