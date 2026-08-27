"""promptech_cc.app — bootstrap (janela pura + Gtk.main, sem GApplication).

Use Gtk.main() direto (padrão do v3 legado, funcional em Wayland):
GApplication exige session bus/DBus estável no subprocesso, o que o
runtime atual (nohup/autostart) não garante — ver v3.py histórico.
"""
import os

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

os.environ.setdefault("GDK_BACKEND", "wayland")

from .window import CommandCenter  # noqa: E402

CSS = b"""
.root { background: rgba(11,16,30,0.96); border-radius: 14px; border: 1px solid #2a3b5c; }
.title { color: #8ab4ff; font-weight: bold; font-size: 13px; padding: 2px; }
#search-entry { background: #131c33; color: #dce7ff; border-radius: 8px;
                border: 1px solid #33507f; padding: 6px 10px; font-size: 13px; }
#search-entry:focus { border-color: #5b8def; }
.prompt-row { background: transparent; color: #dce7ff; border: 1px solid transparent;
              border-radius: 8px; padding: 6px 10px; font-size: 12px; }
.prompt-row:hover { background: #1a2947; border-color: #33507f; }
.act { background: #16223c; color: #dce7ff; border: 1px solid #33507f;
       border-radius: 10px; font-size: 13px; min-height: 34px; padding: 4px 10px; }
.act:hover { background: #1d3050; }
.stat { color: #6f83ad; font-size: 10px; padding: 4px 8px; }
scrollbar { background: transparent; }
"""


def _apply_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def main():
    _apply_css()
    win = CommandCenter()
    win.show_all()
    if os.environ.get("PROMPTECH_SMOKE"):
        delay_ms = int(os.environ.get("PROMPTECH_SMOKE_MS", "1200"))
        from gi.repository import GLib
        GLib.timeout_add(delay_ms, lambda: (
            print(f"GUI_SMOKE_PASS rows={win.listbox.get_children().__len__()}", flush=True),
            Gtk.main_quit()) and False)
    Gtk.main()


if __name__ == "__main__":
    main()