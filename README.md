# Murmur

> Press a key. Speak. Get text. — A minimal, local-first dictation tool inspired by [Wispr Flow](https://wisprflow.ai/).

Murmur is a personal voice-to-text dictation tool for macOS and Windows. Hold a hotkey, speak, release — your words appear at the cursor. Runs **locally by default** via [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper), with an optional OpenAI Whisper API backend.

## Why another one?

[Wispr Flow](https://wisprflow.ai/) is excellent but closed-source, subscription-based, and full of features I don't need. Murmur is what I want: a single hotkey, a single job, a single binary I own.

## Status

🚧 **v0.2** — push-to-talk hotkey + system tray. See [ROADMAP.md](ROADMAP.md).

## Features (v1.0 target)

- 🎙️  Push-to-talk global hotkey (default `fn` on macOS, `right alt` on Windows)
- 🧠 Local Whisper transcription (no internet required)
- 🔌 Pluggable backend: switch to OpenAI API with one click
- 📋 Auto-paste at cursor, fallback to clipboard
- 🪶 Menu bar / system tray app — no Dock icon
- ⚙️  Settings UI for hotkey, model size, language, backend

## Non-goals

- AI rewriting / grammar fixing (use a separate tool)
- Cloud sync, accounts, teams
- Real-time streaming transcription
- Mobile platforms

## Quick start

The bundled `start.sh` installs [uv](https://github.com/astral-sh/uv) (if missing), pins Python via `.python-version`, creates an isolated venv, installs deps, and launches Murmur. **You do not need a system Python — uv installs it.**

```bash
git clone https://github.com/jajajalalalala/murmur.git
cd murmur
./start.sh              # default: launches the menu-bar tray app
./start.sh --cli        # CLI mode (Enter to start/stop)
./start.sh --setup-only # install dependencies, don't launch
./start.sh --reset      # wipe .venv and reinstall
```

The first run downloads a Whisper model (~150 MB for `base`).

### Default hotkey
- macOS: `right Option (⌥)` — hold to record, release to transcribe
- Windows: `right Alt`

Edit the `hotkey` field in the config file (printed by `murmur --show-config`) to change it. Format follows [pynput hotkey syntax](https://pynput.readthedocs.io/en/latest/keyboard.html#monitoring-the-keyboard) — e.g. `<f9>`, `<ctrl>+<shift>+<space>`.

### macOS permissions

On first run macOS will prompt for two permissions — both are required:
1. **Microphone** — needed to record audio
2. **Input Monitoring** — needed for the global push-to-talk hotkey
   (System Settings → Privacy & Security → Input Monitoring → enable your terminal/Murmur)

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for module layout and data flow.

## Roadmap

See [ROADMAP.md](ROADMAP.md). TL;DR:

- **v0.1** ✅ CLI: record → transcribe → clipboard
- **v0.2** Global hotkey + tray icon
- **v0.3** Auto-paste at cursor + recording HUD
- **v1.0** Settings UI + packaged `.app` / `.exe` + GitHub release
- **v1.1+** Custom vocabulary, history, AI rewrite (opt-in)

## License

MIT
