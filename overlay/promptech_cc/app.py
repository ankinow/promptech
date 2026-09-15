"""promptech_cc.app — bootstrap (janela pura + Gtk.main, sem GApplication).

Use Gtk.main() direto (padrão do v3 legado, funcional em Wayland):
GApplication exige session bus/DBus estável no subprocesso, o que o
runtime atual (nohup/autostart) não garante — ver v3.py histórico.
"""
import atexit
import os
import signal
import sys

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

os.environ.setdefault("GDK_BACKEND", "wayland")

from .window import CommandCenter  # noqa: E402

PID_FILE = os.path.join(os.path.expanduser("~"), ".local/state/promptech-cc.pid")

CSS = b"""
* {
    font-family: "Fira Sans", "Cantarell", "Ubuntu", -apple-system, sans-serif;
}
.root {
    background: rgba(11, 16, 30, 0.96);
    border-radius: 14px;
    border: 1px solid #2a3b5c;
    padding: 6px;
}
.title {
    color: #8ab4ff;
    font-weight: bold;
    font-size: 18px;
    padding: 4px 6px;
}
#search-entry {
    background: #131c33;
    color: #dce7ff;
    border-radius: 10px;
    border: 1px solid #33507f;
    padding: 10px 14px;
    font-size: 16px;
    min-height: 46px;
}
#search-entry:focus {
    border-color: #5b8def;
    background: #16223c;
}
.prompt-row {
    background: transparent;
    color: #dce7ff;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
}
.prompt-row:hover, .prompt-row:selected {
    background: #1a2947;
    border-color: #33507f;
}
.act {
    background: #16223c;
    color: #dce7ff;
    border: 1px solid #33507f;
    border-radius: 10px;
    font-size: 14px;
    min-height: 42px;
    padding: 8px 14px;
}
.act:hover {
    background: #1d3050;
    border-color: #5b8def;
}
.stat {
    color: #8fa5cf;
    font-size: 12px;
    padding: 4px 8px;
}
.badge {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    background: #1f3152;
    color: #8ab4ff;
    border-radius: 4px;
    padding: 2px 6px;
}
scrollbar {
    background: transparent;
}
scrollbar trough {
    background: transparent;
}
scrollbar slider {
    background: #2a3b5c;
    border-radius: 4px;
    min-width: 6px;
}
"""


def _apply_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def _check_single_instance() -> bool:
    """Gerencia instância única: se já houver processo vivo, sinaliza para toggle/fechamento."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            if old_pid != os.getpid():
                is_alive = False
                try:
                    os.kill(old_pid, 0)
                    is_alive = True
                except PermissionError:
                    is_alive = True
                except (ProcessLookupError, OSError):
                    is_alive = False

                if is_alive:
                    try:
                        os.kill(old_pid, signal.SIGTERM)
                    except OSError:
                        pass
                    return False
                else:
                    try:
                        os.remove(PID_FILE)
                    except OSError:
                        pass
        except (ValueError, OSError):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except OSError:
        pass
    return True


def _cleanup_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(PID_FILE)
    except (OSError, ValueError):
        pass


def main():
    if not _check_single_instance():
        sys.exit(0)

    atexit.register(_cleanup_pid)

    def _sig_handler(signum, frame):
        _cleanup_pid()
        Gtk.main_quit()

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except ValueError:
        pass

    _apply_css()
    win = CommandCenter()
    win.show_all()
    win.present_with_time(Gdk.CURRENT_TIME)

    if os.environ.get("PROMPTECH_SMOKE"):
        delay_ms = int(os.environ.get("PROMPTECH_SMOKE_MS", "1200"))
        from gi.repository import GLib

        GLib.timeout_add(
            delay_ms,
            lambda: (
                print(
                    f"GUI_SMOKE_PASS rows={len(win.listbox.get_children())}",
                    flush=True,
                ),
                Gtk.main_quit(),
            )
            and False,
        )

    Gtk.main()
    _cleanup_pid()


if __name__ == "__main__":
    main()
