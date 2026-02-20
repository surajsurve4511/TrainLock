# TrainLock 🔒

**Disable keyboard & mouse while your ML model trains — without locking the session.**

A fullscreen GTK3 overlay that blocks all input on the current screen, displays a warning message, and only unlocks when the correct password is entered. Works natively on **Wayland** and X11.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![GTK3](https://img.shields.io/badge/GTK3-native-green)
![Wayland](https://img.shields.io/badge/Wayland-supported-orange)

## Features

- **Fullscreen overlay** — covers the entire screen with a warning message
- **Password-protected unlock** — type password + Enter to unlock
- **Mouse blocked at kernel level** — uses `evdev` to grab pointer devices (no mouse movement at all)
- **Keyboard captured** — all key presses go to the lock screen, nothing reaches other apps
- **Auto-relock watchdog** — optional script that re-locks if someone manages to unlock
- **Wayland native** — uses GTK3, works perfectly on modern Ubuntu/GNOME Wayland sessions
- **No session lock** — does NOT use `loginctl lock-session`, your session stays active

## Requirements

```bash
# Ubuntu / Debian
sudo apt install python3-gi gir1.2-gtk-3.0 python3-evdev

# Add yourself to input group (for mouse blocking via evdev)
sudo usermod -aG input $USER
# Log out and back in for group change to take effect
```

## Usage

### Quick lock

```bash
./trainlock.sh                    # default password: train123
./trainlock.sh mySecretPassword   # custom password
```

### With auto-relock watchdog

Run in one terminal:
```bash
./trainlock_watchdog.sh &         # starts lock + auto-relocks if unlocked
python train_rl.py                # run your training
kill %1                           # stop watchdog when training finishes
```

### Unlock

| Method | How |
|--------|-----|
| **Password** | Type the password and press **Enter** |
| **Secret shortcut** | Press **Ctrl+Alt+U** (instant unlock, not shown on screen) |

### Emergency unlock

If something goes wrong:
1. Switch to a text TTY: **Ctrl+Alt+F2**
2. Log in with your system credentials
3. Kill the lock: `kill $(pgrep -f rl_input_lock.py)`

## Files

| File | Description |
|------|-------------|
| `rl_input_lock.py` | Main lock screen (GTK3 + evdev) |
| `trainlock.sh` | Launcher script with dependency checks |
| `trainlock_watchdog.sh` | Auto-relock watchdog daemon |

## How it works

1. A fullscreen GTK3 window covers the screen with `keep_above` + `SPLASHSCREEN` type hint
2. All keyboard input is captured by the GTK window — only the password entry receives keys
3. Mouse/touchpad devices are grabbed at the Linux kernel level via `evdev`, so the pointer is completely frozen
4. The window re-focuses itself every 500ms to prevent being pushed behind other windows
5. On unlock, all grabbed devices are released and the overlay closes

## License

MIT
