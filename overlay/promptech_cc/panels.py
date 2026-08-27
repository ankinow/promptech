"""promptech_cc.panels — builders de UI (lista de prompts e painel de ações)."""
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class PromptRow(Gtk.ListBoxRow):
    def __init__(self, trigger: str, label: str):
        super().__init__()
        self.trigger = trigger
        self.label = label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class("prompt-row")
        t = Gtk.Label(xalign=0)
        t.set_markup(f"<b>{_esc(trigger)}</b>")
        l = Gtk.Label(xalign=0, hexpand=True)
        l.set_text(label or trigger)
        l.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        box.pack_start(t, False, False, 0)
        box.pack_start(l, True, True, 0)
        self.add(box)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_prompts_panel():
    """Retorna (listbox, container_left)."""
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_size_request(280, 240)
    scroll.add(listbox)
    left.pack_start(scroll, True, True, 0)
    return listbox, left


def build_actions_panel(win):
    """Painel direito: botões ligados a callbacks da window."""
    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    actions = [
        ("🎙  Ditado heard", win.dictate_heard),
        ("⌨  Ditado whisper", win.dictate_whisper),
        ("🔍  Espanso search", win.open_espanso_search),
        ("➕  Novo prompt", win.new_prompt_dialog),
        ("✎  Revisar base.yml", win.action_review_yml),
        ("📄  Logs", win.show_logs_dialog),
    ]
    for label, cb in actions:
        b = Gtk.Button(label=label)
        b.get_style_context().add_class("act")
        b.set_tooltip_text(label)
        b.connect("clicked", lambda _b, fn=cb: fn())
        right.pack_start(b, False, False, 0)
    return right
