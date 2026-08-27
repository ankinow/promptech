#!/usr/bin/env python3
"""heard/promptech command center — GTK3 floating overlay (~10-30MB RAM vs 78 PyQt6)."""
import os
import subprocess

os.environ.setdefault("GDK_BACKEND", "wayland")  # obrigatório sob KWin Wayland — sem isso a janela não renderiza
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

CSS = b"""
.root { background: rgba(13,20,36,0.93); border-radius: 14px; border: 1px solid #2a3b5c; }
button { background: transparent; color: #dce7ff; border: 1px solid #33507f;
         border-radius: 10px; font-size: 17px; min-width: 42px; min-height: 42px; padding: 4px; }
button:hover { background: #1d3050; }
"""

_HOME = os.path.expanduser("~")

ACTIONS = [
    ("🎙", "Ditado (heard)", f"{_HOME}/bin/dictate-heard.sh"),
    ("🔍", "Prompt search", "espanso cmd search"),
    ("⌨", "Ditado local (whisper)", f"{_HOME}/bin/dictate-whisper.sh"),
    ("➕", "Adicionar/editar prompts", "bash -c 'xdg-open ~/.config/espanso/match/base.yml || espanso edit'"),
]


def run(cmd):
    subprocess.Popen(["bash", "-c", cmd])


win = Gtk.Window()
win.set_title("promptech")
win.set_type_hint(Gdk.WindowTypeHint.TOOLBAR)  # sem entrada na taskbar
win.set_keep_above(True)
win.set_decorated(False)
win.set_resizable(False)
win.set_accept_focus(True)

box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
              margin_top=10, margin_bottom=10, margin_start=8, margin_end=8)
box.get_style_context().add_class("root")

for icon, tip, cmd in ACTIONS:
    b = Gtk.Button(label=icon)
    b.set_tooltip_text(tip)
    b.connect("clicked", lambda _b, c=cmd: run(c))
    box.pack_start(b, False, False, 0)

win.add(box)


def reposition():
    # Wayland: move() só surte efeito DEPOIS do mapeamento completo — daí o timeout
    disp = Gdk.Display.get_default()
    mon = disp.get_monitor_at_window(win.get_window())
    g = mon.get_geometry()
    win.move(g.x + g.width - 80, g.y + 180)  # borda direita do monitor real
    return False  # roda 1x


def on_map(*_a):
    GLib.timeout_add(200, reposition)


win.connect("map", on_map)

css = Gtk.CssProvider()
css.load_from_data(CSS)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

win.show_all()
Gtk.main()
