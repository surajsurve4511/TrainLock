#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  RL Training Input Lock — Launcher
# ═══════════════════════════════════════════════════════════════════
#  Disables mouse & keyboard on the CURRENT screen (no session lock).
#  Displays a fullscreen warning overlay.
#
#  Unlock methods:
#    • Type password + Enter
#    • Press Ctrl+Alt+U
#
#  Usage:
#    ./rl_training_lock_v2.sh                  # default pwd: train123
#    ./rl_training_lock_v2.sh mySecretPass     # custom  pwd
#
#  Emergency unlock (if something goes wrong):
#    Switch to another TTY:  Ctrl+Alt+F2
#    Log in and run:         kill $(pgrep -f rl_input_lock.py)
#    Then re-enable pointer: xinput --list | grep -i 'slave.*pointer'
#                            xinput enable <id>   (for each device)
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK_SCRIPT="$SCRIPT_DIR/rl_input_lock.py"
PASSWORD="${1:-train123}"
BG_IMAGE="${2:-$HOME/Downloads/rl_lock_wallpaper.png}"

# ── Pre-flight checks ────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "❌  python3 is not installed. Please install it first."
    exit 1
fi

if ! python3 -c "import gi; gi.require_version('Gtk','3.0')" &>/dev/null; then
    echo "❌  PyGObject (GTK3 bindings) not found."
    echo "   Install with:  sudo apt install python3-gi gir1.2-gtk-3.0"
    exit 1
fi

if ! python3 -c "import evdev" &>/dev/null; then
    echo "⚠  python3-evdev not found — mouse will not be blocked at kernel level."
    echo "   Install with:  sudo apt install python3-evdev"
    echo "   And add yourself to the input group:  sudo usermod -aG input \$USER"
    echo ""
fi

if [ ! -f "$LOCK_SCRIPT" ]; then
    echo "❌  Cannot find $LOCK_SCRIPT"
    exit 1
fi

# ── Launch the lock ───────────────────────────────────────────────
echo "🔒 Activating RL Training Input Lock..."
echo "   Session : $XDG_SESSION_TYPE"
echo "   Password: $(printf '*%.0s' $(seq 1 ${#PASSWORD}))"
echo "   Unlock  : type password + Enter  OR  Ctrl+Alt+U"
echo ""

python3 "$LOCK_SCRIPT" "$PASSWORD" --bg "$BG_IMAGE"
