#!/usr/bin/env python3
"""
RL Training Input Lock v2
=========================
Fullscreen GTK3 overlay — works natively on Wayland & X11.
Blocks mouse (kernel‑level via evdev) and captures all keyboard input.
Shows warning message + styled password entry bar.

Unlock:
  1. Type password + Enter
  2. Press Ctrl+Alt+U  (instant, no password)

Usage:
  python3 rl_input_lock.py                           # default password: train123
  python3 rl_input_lock.py mypass                     # custom password
  python3 rl_input_lock.py mypass --bg /path/to.png   # custom background
"""

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import subprocess, signal, sys, os, re, threading, argparse, time

# ── Optional: kernel‑level mouse grab ────────────────────────────
try:
    import evdev
    import evdev.ecodes as ecodes
    HAVE_EVDEV = True
except ImportError:
    HAVE_EVDEV = False

DEFAULT_PASSWORD = "train123"
DEFAULT_BG = os.path.expanduser("~/Downloads/rl_lock_wallpaper.png")

# ══════════════════════════════════════════════════════════════════
#  GTK CSS  (native styling — works on both X11 & Wayland)
# ══════════════════════════════════════════════════════════════════
CSS = """
/* dark fullscreen background */
#lock-window {
    background-color: #0a0a1a;
}

/* semi-transparent box behind the text */
#warning-eventbox {
    background-color: rgba(10, 0, 0, 0.88);
    border-radius: 22px;
}

/* ── labels ─────────────────────────────────────────────── */
.warning-title  { color: #ff4444; font-size: 38px; font-weight: bold; }
.training-text  { color: #ffffff; font-size: 28px; font-weight: bold; }
.info-text      { color: #aaaaaa; font-size: 20px; }
.marathi-text   { color: #ffdd88; font-size: 18px; font-family: "Lohit Devanagari", "Lohit Deva Marathi", "Gargi", "Sarai", "Noto Sans Devanagari", sans-serif; }
.unlock-hint    { color: #888888; font-size: 14px; }
.password-label { color: #cccccc; font-size: 18px; }

.error-text   { color: #ff4444; font-size: 16px; font-weight: bold; }
.success-text { color: #66ff66; font-size: 16px; font-weight: bold; }

/* ── password field ─────────────────────────────────────── */
.password-entry {
    background: #1a1a2e;
    color: #66ff66;
    border: 2px solid #4444ff;
    border-radius: 12px;
    padding: 8px 16px;
    font-size: 22px;
    min-width: 350px;
    min-height: 24px;
    caret-color: #66ff66;
}
.password-entry:focus {
    border-color: #8888ff;
}

/* red border around the whole content area */
#warning-frame {
    border: 3px solid #ff4444;
    border-radius: 22px;
    padding: 4px;
}
"""


# ══════════════════════════════════════════════════════════════════
#  LockScreen  —  the fullscreen window
# ══════════════════════════════════════════════════════════════════
class LockScreen(Gtk.Window):

    def __init__(self, password, bg_image=None):
        super().__init__(title="RL Training Lock")
        self.password = password
        self.locked = True
        self.grabbed_devices = []          # evdev InputDevice objects

        # ── Apply CSS ─────────────────────────────────────────────
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # ── Window flags ──────────────────────────────────────────
        self.set_name("lock-window")
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)
        self.set_keep_above(True)
        self.fullscreen()
        self.connect('delete-event', lambda w, e: True)   # block close

        # ── Screen geometry ───────────────────────────────────────
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geom = monitor.get_geometry()
        self.sw, self.sh = geom.width, geom.height

        # ── Build the UI ──────────────────────────────────────────
        self._build_ui(bg_image)

        # ── Input handling ────────────────────────────────────────
        self.connect('key-press-event', self._on_key_press)

        # Re-focus periodically so window can't stay behind
        GLib.timeout_add(500, self._refocus)

        # ── Grab mouse devices (evdev) ────────────────────────────
        if HAVE_EVDEV:
            GLib.idle_add(self._grab_pointer_devices)

        # ── Signals ───────────────────────────────────────────────
        signal.signal(signal.SIGTERM, self._sig)
        signal.signal(signal.SIGINT,  self._sig)

        self.show_all()
        GLib.idle_add(self._hide_cursor)

    # ──────────────────────────────────────────────────────────────
    #  UI
    # ──────────────────────────────────────────────────────────────
    def _build_ui(self, bg_image):
        overlay = Gtk.Overlay()
        self.add(overlay)

        # ── Background (solid dark colour) ─────────────────────────
        bg_widget = self._solid_bg()
        overlay.add(bg_widget)

        # ── Content area (centred box with red border) ────────────
        frame = Gtk.Frame()
        frame.set_name("warning-frame")
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        frame.set_halign(Gtk.Align.CENTER)
        frame.set_valign(Gtk.Align.CENTER)

        ebox = Gtk.EventBox()
        ebox.set_name("warning-eventbox")
        frame.add(ebox)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vbox.set_margin_top(40);    vbox.set_margin_bottom(40)
        vbox.set_margin_start(60);  vbox.set_margin_end(60)
        ebox.add(vbox)

        # ── Warning text ──────────────────────────────────────────
        self._label(vbox, "⚠   DO NOT SWITCH OFF THIS PC   ⚠",
                    'warning-title', bottom=8)
        sep = Gtk.Separator()
        vbox.pack_start(sep, False, False, 4)

        self._label(vbox, "Reinforcement Learning Model Training",
                    'training-text')
        self._label(vbox, "is currently IN PROGRESS",
                    'training-text', bottom=10)

        self._label(vbox, "Please do NOT use or shut down this PC.",
                    'info-text', bottom=8)

        self._label(vbox, "आरएल मॉडेल ट्रेनिंग चालू आहे।",
                    'marathi-text')
        self._label(vbox, "कृपया हा पीसी बंद करू नका आणि वापरू नका।",
                    'marathi-text', bottom=10)

        sep2 = Gtk.Separator()
        vbox.pack_start(sep2, False, False, 4)

        self._label(vbox,
                    "Enter password to unlock this screen",
                    'unlock-hint', bottom=10)

        # ── Password row ──────────────────────────────────────────
        pw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        pw_row.set_halign(Gtk.Align.CENTER)
        vbox.pack_start(pw_row, False, False, 4)

        pw_lbl = Gtk.Label(label="Password:")
        pw_lbl.get_style_context().add_class('password-label')
        pw_row.pack_start(pw_lbl, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_visibility(False)
        self.entry.set_invisible_char('\u25cf')  # ●
        self.entry.set_placeholder_text("Enter password\u2026")
        self.entry.get_style_context().add_class('password-entry')
        self.entry.connect('activate', self._check_password)   # Enter key
        pw_row.pack_start(self.entry, False, False, 0)

        # ── Status label ──────────────────────────────────────────
        self.status = Gtk.Label(label="")
        self.status.get_style_context().add_class('error-text')
        vbox.pack_start(self.status, False, False, 4)

        overlay.add_overlay(frame)

    # ── helpers ───────────────────────────────────────────────────
    @staticmethod
    def _label(box, text, css_class, bottom=0):
        l = Gtk.Label(label=text)
        l.get_style_context().add_class(css_class)
        l.set_margin_bottom(bottom)
        box.pack_start(l, False, False, 0)

    def _solid_bg(self):
        eb = Gtk.EventBox()
        eb.set_name("lock-window")
        eb.set_size_request(self.sw, self.sh)
        return eb

    def _hide_cursor(self):
        w = self.get_window()
        if w:
            cur = Gdk.Cursor.new_for_display(
                w.get_display(), Gdk.CursorType.BLANK_CURSOR)
            w.set_cursor(cur)
        return False

    # ──────────────────────────────────────────────────────────────
    #  Focus / re-present
    # ──────────────────────────────────────────────────────────────
    def _refocus(self):
        if not self.locked:
            return False
        try:
            self.present()
            self.set_keep_above(True)
            self.fullscreen()
            if not self.entry.has_focus():
                self.entry.grab_focus()
        except Exception:
            pass
        return True          # keep timer alive

    # ──────────────────────────────────────────────────────────────
    #  Keyboard
    # ──────────────────────────────────────────────────────────────
    def _on_key_press(self, widget, event):
        name = Gdk.keyval_name(event.keyval) or ""
        st   = event.state
        ctrl = bool(st & Gdk.ModifierType.CONTROL_MASK)
        alt  = bool(st & Gdk.ModifierType.MOD1_MASK)

        # Ctrl+Alt+U -> instant unlock
        if name.lower() == 'u' and ctrl and alt:
            self._unlock()
            return True

        # Swallow dangerous WM combos (best-effort on Wayland)
        if alt and name in ('Tab', 'F4', 'F1', 'F2', 'F3'):
            return True
        if name in ('Super_L', 'Super_R'):
            return True

        # Everything else -> propagate to Entry
        if not self.entry.has_focus():
            self.entry.grab_focus()
        return False

    def _check_password(self, entry):
        user_input = entry.get_text().strip()  # Remove whitespace
        if user_input == self.password:
            self.status.set_text("\u2713  Unlocking\u2026")
            sc = self.status.get_style_context()
            sc.remove_class('error-text')
            sc.add_class('success-text')
            GLib.timeout_add(250, self._unlock)
        else:
            entry.set_text("")
            self.status.set_text("\u2717  Wrong password \u2014 try again")
            sc = self.status.get_style_context()
            sc.remove_class('success-text')
            sc.add_class('error-text')

    # ──────────────────────────────────────────────────────────────
    #  evdev — grab pointer/touchpad devices at kernel level
    #  (keyboard is NOT grabbed -> GTK still receives key events)
    # ──────────────────────────────────────────────────────────────
    def _grab_pointer_devices(self):
        if not HAVE_EVDEV:
            return False
        try:
            for path in evdev.list_devices():
                d = evdev.InputDevice(path)
                caps = d.capabilities()
                is_pointer = (ecodes.EV_REL in caps or ecodes.EV_ABS in caps)
                if is_pointer:
                    try:
                        d.grab()
                        self.grabbed_devices.append(d)
                        print(f"  \u2713 Grabbed pointer: {d.name}")
                    except (PermissionError, OSError) as e:
                        print(f"  \u2717 Cannot grab {d.name}: {e}")
                        d.close()
                else:
                    d.close()
        except Exception as e:
            print(f"  evdev error: {e}")
        return False

    def _release_pointer_devices(self):
        for d in self.grabbed_devices:
            try:
                d.ungrab()
            except Exception:
                pass
            try:
                d.close()
            except Exception:
                pass
        self.grabbed_devices.clear()

    # ──────────────────────────────────────────────────────────────
    #  Unlock
    # ──────────────────────────────────────────────────────────────
    def _unlock(self):
        if not self.locked:
            return False
        self.locked = False
        self._release_pointer_devices()
        # Restore cursor before we go
        w = self.get_window()
        if w:
            w.set_cursor(None)
        self.destroy()
        Gtk.main_quit()
        return False

    def _sig(self, signum, frame):
        GLib.idle_add(self._unlock)


# ══════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════
def main():
    p = argparse.ArgumentParser(description="RL Training Input Lock")
    p.add_argument('password', nargs='?', default=DEFAULT_PASSWORD,
                   help=f"Unlock password (default: {DEFAULT_PASSWORD})")
    p.add_argument('--bg', default=DEFAULT_BG,
                   help="Background image path")
    args = p.parse_args()

    print("\u2554" + "\u2550" * 50 + "\u2557")
    print("\u2551      RL Training Input Lock v2 \u2014 ACTIVATED      \u2551")
    print("\u2560" + "\u2550" * 50 + "\u2563")
    print(f"\u2551  Password  : {'*' * len(args.password):42s}  \u2551")
    print("\u2551  Unlock    : type password + Enter              \u2551")
    print("\u2551             : OR press Ctrl+Alt+U               \u2551")
    print("\u2551  Emergency : Ctrl+Alt+F2 \u2192 login TTY \u2192 kill PID\u2551")
    print(f"\u2551  PID       : {os.getpid():<42d}  \u2551")
    print(f"\u2551  evdev     : {'Yes' if HAVE_EVDEV else 'No (mouse grab unavail)':42s}  \u2551")
    print("\u255a" + "\u2550" * 50 + "\u255d")

    LockScreen(password=args.password, bg_image=args.bg)
    Gtk.main()

    print("\n\u2705  Input lock released. You may use the PC now.\n")


if __name__ == "__main__":
    main()
