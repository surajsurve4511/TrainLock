#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  RL Training Watchdog v2
# ═══════════════════════════════════════════════════════════════════
#  Monitors the rl_input_lock.py process.
#  If someone unlocks it, the watchdog re-locks after a grace period.
#
#  Usage:
#    ./rl_watchdog_v2.sh &                # run in background
#    python train_rl.py                   # start your training
#
#  When training finishes:
#    kill $(pgrep -f rl_watchdog_v2)      # stop the watchdog
#
#  Or use the combined command:
#    ./rl_watchdog_v2.sh &
#    python train_rl.py ; kill %1         # auto-stop watchdog when
#                                         # training completes
# ═══════════════════════════════════════════════════════════════════

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCK_LAUNCHER="$SCRIPT_DIR/trainlock.sh"
PASSWORD="${1:-train123}"

RELOCK_DELAY=10    # seconds to wait before re-locking after an unlock
CHECK_INTERVAL=5   # seconds between alive-checks

echo "╔══════════════════════════════════════════════════╗"
echo "║    RL Training Watchdog v2  — STARTED            ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Re-lock delay : ${RELOCK_DELAY}s after unlock              ║"
echo "║  Stop watchdog : kill $$                        ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

chmod +x "$LOCK_LAUNCHER"

cleanup() {
    echo ""
    echo "🛑  Watchdog stopped. Killing any running lock overlay..."
    pkill -f "rl_input_lock.py" 2>/dev/null || true
    # Re-enable all pointer devices in case lock was killed uncleanly
    for id in $(xinput list --id-only 2>/dev/null); do
        xinput enable "$id" 2>/dev/null || true
    done
    echo "✅  All input devices re-enabled. Done."
    exit 0
}

trap cleanup SIGTERM SIGINT EXIT

# ── Initial lock ──────────────────────────────────────────────────
bash "$LOCK_LAUNCHER" "$PASSWORD" &
LOCK_PID=$!
echo "🔒 Lock started (PID $LOCK_PID)"

while true; do
    sleep "$CHECK_INTERVAL"

    # Is the lock process still running?
    if ! kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "⚠  Lock was closed / unlocked!"
        echo "   Re-locking in ${RELOCK_DELAY}s..."
        sleep "$RELOCK_DELAY"

        bash "$LOCK_LAUNCHER" "$PASSWORD" &
        LOCK_PID=$!
        echo "🔒 Re-locked (PID $LOCK_PID)"
    fi
done
