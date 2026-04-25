#!/usr/bin/env bash
# Murmur setup + run script.
# - Installs uv if missing
# - Pins Python via .python-version
# - Creates an isolated venv
# - Installs the project + GUI extras
# - Launches Murmur
#
# Usage:
#   ./start.sh                  # set up (if needed) and launch GUI
#   ./start.sh --cli            # set up (if needed) and launch CLI mode
#   ./start.sh --setup-only     # only install + sync, don't launch
#   ./start.sh --reset          # wipe .venv and reinstall from scratch

set -euo pipefail

cd "$(dirname "$0")"

LAUNCH_MODE="gui"
SETUP_ONLY=0
RESET=0

for arg in "$@"; do
    case "$arg" in
        --cli) LAUNCH_MODE="cli" ;;
        --setup-only) SETUP_ONLY=1 ;;
        --reset) RESET=1 ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

# 1. Install uv if missing.
if ! command -v uv >/dev/null 2>&1; then
    echo "[start.sh] uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # uv installs to ~/.local/bin; make sure it's on PATH for this shell.
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "[start.sh] uv: $(uv --version)"

# 2. Reset venv if requested.
if [[ $RESET -eq 1 ]]; then
    echo "[start.sh] --reset: removing .venv"
    rm -rf .venv
fi

# 3. Ensure pinned Python is installed.
PINNED_PYTHON="$(cat .python-version 2>/dev/null || echo 3.11)"
echo "[start.sh] target Python: $PINNED_PYTHON"
uv python install "$PINNED_PYTHON" >/dev/null

# 4. Create venv if missing.
if [[ ! -d .venv ]]; then
    echo "[start.sh] creating .venv with Python $PINNED_PYTHON"
    uv venv --python "$PINNED_PYTHON"
fi

# 5. Install project + GUI extras (idempotent).
echo "[start.sh] installing project + GUI deps (this may take a few minutes the first time)..."
uv pip install -e ".[gui]"

# Optional: also install the openai extra if user has set OPENAI_API_KEY
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
    echo "[start.sh] OPENAI_API_KEY detected — installing [openai] extra"
    uv pip install -e ".[openai]"
fi

if [[ $SETUP_ONLY -eq 1 ]]; then
    echo "[start.sh] setup complete. Run ./start.sh to launch."
    exit 0
fi

# 6. Launch.
if [[ "$LAUNCH_MODE" == "cli" ]]; then
    echo "[start.sh] launching CLI mode..."
    exec .venv/bin/murmur --cli
else
    echo "[start.sh] launching GUI..."
    exec .venv/bin/murmur
fi
