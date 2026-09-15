"""promptech_cc.window — janela principal (busca + lista + ações + status)."""
import os
import subprocess
import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: F401  (GLib p/ typing futuro)

from . import services
from .dialogs import LogsDialog, NewPromptDialog, SettingsDialog
from .panels import PromptRow, build_actions_panel, build_prompts_panel


class CommandCenter(Gtk.Window):
    """Overlay always-on-top estilo Hermes: busca, lista, ações, status."""

    def __init__(self):
        super().__init__(title="promptech")
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(960, 620)
        self.set_position(Gtk.WindowPosition.CENTER)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                       margin_top=14, margin_bottom=12, margin_start=14, margin_end=14)
        root.get_style_context().add_class("root")

        self._build_header(root)
        self._build_search(root)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        root.pack_start(body, True, True, 0)

        self.listbox, left = build_prompts_panel()
        self.listbox.connect("row-activated", self._on_row_activated)
        body.pack_start(left, True, True, 0)

        actions_box = build_actions_panel(self)
        body.pack_start(actions_box, False, False, 0)

        self.stat = Gtk.Label(xalign=0)
        self.stat.get_style_context().add_class("stat")
        root.pack_start(self.stat, False, False, 0)

        self.add(root)
        self.reload()
        self.connect("key-press-event", self._on_key)

    # ---- construção ----
    def _build_header(self, root):
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(xalign=0)
        title.get_style_context().add_class("title")
        title.set_markup(
            "⚡ promptech <span foreground='#6f83ad' size='larger'>command center</span>")
        head.pack_start(title, True, True, 0)
        close = Gtk.Button(label="✕")
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.connect("clicked", lambda *_: Gtk.main_quit())
        head.pack_end(close, False, False, 0)

        head_ev = Gtk.EventBox()
        head_ev.add(head)
        head_ev.connect("button-press-event", self._on_header_drag)
        root.pack_start(head_ev, False, False, 0)

    def _on_header_drag(self, _widget, event):
        if event.button == 1:
            win = self.get_window()
            if win:
                win.begin_move_drag(
                    event.button,
                    int(event.x_root),
                    int(event.y_root),
                    event.time
                )
                return True
        return False

    def _build_search(self, root):
        self.search = Gtk.SearchEntry()
        self.search.set_name("search-entry")
        self.search.set_placeholder_text("Buscar prompt… (digite trigger, label ou conteúdo)")
        self.search.connect("search-changed", self._filter)
        self.search.connect("activate", self._copy_first)
        root.pack_start(self.search, False, False, 0)

    # ---- prompts ----
    def reload(self):
        for c in self.listbox.get_children():
            self.listbox.remove(c)
        self._all = services.parse_base_yml(services.base_yml())
        for trigger, label in self._all:
            self.listbox.add(PromptRow(trigger, label))
        self.listbox.show_all()
        n = len(self._all)
        up = services.uptime_hours()
        up_s = f"{up}h" if up is not None else "?"
        self.stat.set_text(f"{n} prompts · espanso: {services.espanso_status()} · uptime {up_s}")

    def _filter(self, _e):
        q = self.search.get_text().lower().strip()
        for row in self.listbox.get_children():
            if not q:
                row.set_visible(True)
                continue
            hay = (row.trigger + " " + row.label).lower()
            if q in hay:
                row.set_visible(True)
            else:
                body = services.read_prompt_body(row.trigger).lower()
                row.set_visible(q in body)

    def _visible_rows(self):
        return [r for r in self.listbox.get_children() if r.get_visible()]

    def _on_row_activated(self, _lb, row):
        self._copy_row(row)

    def _copy_row(self, row):
        text = services.read_prompt_body(row.trigger)
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(text, -1)
        cb.store()
        services.notify("promptech", f"copiado: {row.trigger}")
        services.log(f"copy trigger={row.trigger}")
        Gtk.main_quit()

    def _copy_first(self, *_a):
        rows = self._visible_rows()
        if rows:
            self.listbox.select_row(rows[0])
            self._copy_row(rows[0])

    # ---- ações ----
    def new_prompt_dialog(self):
        dlg = NewPromptDialog(self)
        resp = dlg.run()
        if resp == Gtk.ResponseType.OK:
            err = dlg.save()
            if err:
                services.notify("promptech", f"erro ao salvar: {err}")
            else:
                self.reload()
        dlg.destroy()

    def show_settings_dialog(self):
        dlg = SettingsDialog(parent=self)
        resp = dlg.run()
        if resp == Gtk.ResponseType.OK:
            dlg.save()
            self.reload()
        dlg.destroy()

    def show_logs_dialog(self):
        dlg = LogsDialog(parent=self)
        dlg.run()
        dlg.destroy()

    def spawn_action(self, cmd: list, timeout: int = 10):
        err = services.run_action(cmd, timeout=timeout)
        if err:
            services.notify("promptech", f"ação falhou: {err}")

    def action_review_yml(self):
        self.spawn_action(["xdg-open", services.base_yml()], timeout=5)

    def open_espanso_search(self):
        self.spawn_action(["espanso", "cmd", "search"])

    def run_dictate(self, script_name: str):
        # ditado é longo (gravação + transcrição): sem timeout rígido, mas sync
        path = os.path.join(os.path.expanduser("~"), "bin", script_name)
        try:
            subprocess.Popen(["bash", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)  # fire-and-forget intencional (toggle scripts)
        except OSError as e:
            services.notify("promptech", f"ditado falhou: {e}")

    def dictate_heard(self, _btn=None):
        self.run_dictate("dictate-heard.sh")

    def dictate_whisper(self, _btn=None):
        self.run_dictate("dictate-whisper.sh")

    # ---- teclado/janela ----
    def _on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()
        return False
