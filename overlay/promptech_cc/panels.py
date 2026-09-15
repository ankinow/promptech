"""promptech_cc.panels — builders de UI (lista de prompts e painel de ações)."""
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class PromptRow(Gtk.ListBoxRow):
    def __init__(self, trigger: str, label: str):
        super().__init__()
        self.trigger = trigger
        self.label = label
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                      margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)
        box.get_style_context().add_class("prompt-row")
        
        t = Gtk.Label(xalign=0)
        t.set_markup(f"<b><span font_family='monospace' foreground='#89b4fa'>{_esc(trigger)}</span></b>")
        
        l = Gtk.Label(xalign=0, hexpand=True)
        l.set_text(label or trigger)
        l.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        
        box.pack_start(t, False, False, 0)
        box.pack_start(l, True, True, 0)
        self.add(box)


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_prompts_panel():
    """Retorna (listbox, container_left) com escala expandida."""
    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    listbox = Gtk.ListBox()
    listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
    
    scroll = Gtk.ScrolledWindow()
    scroll.set_vexpand(True)
    scroll.set_hexpand(True)
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_size_request(560, 440)
    scroll.add(listbox)
    
    left.pack_start(scroll, True, True, 0)
    return listbox, left


def build_actions_panel(win):
    """Painel direito: botões ligados a callbacks da window com ícones e tooltips descritivos."""
    right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    actions = [
        ("🎙  Ditado heard", win.dictate_heard, "Gravação e transcrição rápida de voz via whisper heard"),
        ("⌨  Ditado whisper", win.dictate_whisper, "Ditado contínuo whisper com injeção direta"),
        ("🔍  Espanso search", win.open_espanso_search, "Abrir menu de busca nativo do Espanso (Meta+Space)"),
        ("➕  Novo prompt", win.new_prompt_dialog, "Criar novo trigger e salvar no base.yml"),
        ("⚙  Configurações", win.show_settings_dialog, "Abrir painel de configurações (Whisper, Espanso, Backups)"),
        ("✎  Revisar base.yml", win.action_review_yml, "Abrir o arquivo base.yml no editor padrão"),
        ("📄  Logs", win.show_logs_dialog, "Visualizar histórico de logs de ações e erros"),
    ]
    for label, cb, tooltip in actions:
        b = Gtk.Button(label=label)
        b.get_style_context().add_class("act")
        b.set_tooltip_text(tooltip)
        b.connect("clicked", lambda _b, fn=cb: fn())
        right.pack_start(b, False, False, 0)
    return right
