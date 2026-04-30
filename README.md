# Murmur

> Press a key. Speak. Get text.

[![Latest release](https://img.shields.io/github/v/release/jajajalalalala/murmur?display_name=tag&sort=semver)](https://github.com/jajajalalalala/murmur/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<!--
TODO(hero-gif): record a 5-second GIF of a real recording (hold key, speak,
release, watch text appear) and drop it in `assets/hero.gif`, then replace
this comment with:

    ![Murmur in action](assets/hero.gif)

Until then we ship a clean README without a broken-image badge.
-->

## What Murmur is

Murmur is a free, local-first dictation tool for macOS. Hold a hotkey, speak, release — and your words appear at the cursor. No accounts, no cloud, no telemetry; transcription runs on your laptop by default.

## Install

1. Download the latest `Murmur-*.dmg` from the [Releases page](https://github.com/jajajalalalala/murmur/releases/latest).
2. Open the `.dmg` and drag **Murmur.app** into your Applications folder.
3. The first time you launch it, **right-click Murmur.app and choose Open** (then click Open in the dialog). macOS shows that warning once because v1.0 is unsigned — every launch after that is a normal double-click.

That's it. Murmur lives in your menu bar (look for the small dot near the clock), not the Dock.

## First use

On first launch Murmur asks macOS for **Input Monitoring** (so it can see your push-to-talk hotkey) and opens the main window so you can pick a transcription model. If you skip the prompt, click the Murmur icon in the menu bar → **Open Murmur…** to come back to it.

## Daily use

- **Hold the hotkey** while you talk; release when you're done. The default is **Right Option (⌥)** on the right side of your keyboard.
- A small pill appears at the bottom of your screen while Murmur is recording. The waveform reacts to your voice and the timer counts up.
- Release the key — Murmur transcribes and pastes the text at your cursor (or copies it to the clipboard if your app doesn't support paste-at-cursor).

To change the hotkey: click the menu-bar icon → **Open Murmur…** → **Shortcuts** → click the hotkey field → press the key (or combo) you want. Combos like `⌃⇧Space` are supported. Murmur asks before restarting to apply the change.

## Models

Murmur runs Whisper locally by default — no internet needed once the model is downloaded.

- **Local models** (recommended for privacy) — the **Models** page lists Whisper sizes from `tiny` (~70 MB, fastest) to `large-v3` (~1.5 GB, most accurate). Click **Download**, then **Use**. `base` is a good starting point; `small` is the sweet spot for accuracy on a recent Mac.
- **Cloud models** — to use OpenAI Whisper or any OpenAI-compatible endpoint (Groq, DeepSeek, custom), pick the provider from the **Cloud** dropdown on the Models page and paste your API key. Cloud transcription is faster on big audio but sends your speech to a third party.

## FAQ

**My hotkey doesn't do anything.** Open **System Settings → Privacy & Security → Input Monitoring**, make sure Murmur is enabled, then **quit and relaunch Murmur** — macOS only re-checks the permission at launch.

**The transcribed text doesn't appear in my document.** Murmur uses Accessibility to simulate ⌘V at the cursor. If you didn't grant it, your text still lands on the clipboard — just press ⌘V yourself. To enable real auto-paste, grant Accessibility in System Settings and relaunch.

**"Murmur is damaged and can't be opened."** macOS quarantines unsigned downloads. Right-click `Murmur.app` → **Open** the first time (not double-click), then click **Open** in the dialog.

**I rebuilt or updated Murmur and the hotkey stopped working.** Each rebuild creates a new code identity that the old Input Monitoring entry doesn't cover. In System Settings → Input Monitoring, **remove the old Murmur entry (–)** and re-add or toggle the new one ON.

**How do I uninstall Murmur?** Drag `Murmur.app` to the Trash, then in System Settings → Privacy & Security remove Murmur from Microphone, Input Monitoring, and Accessibility. To also clear downloaded models and config, run `~/Applications/Murmur.app/Contents/MacOS/Murmur --uninstall --yes` from Terminal before deleting the app.

**Where are my transcripts saved?** They aren't. Murmur writes the text to your cursor (or clipboard) and forgets it. The Home page shows the **last 5** transcripts of the current session for quick re-copying — they vanish when you quit.

**My laptop fan spins up during transcription.** Whisper is CPU-heavy. Switch to a smaller model (`tiny` or `base`) on the Models page, or use a cloud backend.

**Something else is broken.** Open an issue on [GitHub](https://github.com/jajajalalalala/murmur/issues) — include your macOS version and what you were doing when it broke. Logs live at `~/Library/Logs/Murmur/murmur.log`.

## Why Murmur

There are good paid dictation apps. There aren't many that respect your privacy and your wallet at the same time. Murmur exists because dictation should be a feature your computer has, not a $15/month subscription that ships your voice to someone else's server. Local Whisper is good enough now that the cloud option is a fallback, not a requirement.

## Hacking on Murmur

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, build, and PR workflow.

## License

MIT — see [LICENSE](LICENSE).
