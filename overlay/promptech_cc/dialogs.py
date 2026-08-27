"""promptech_cc.dialogs — Novo prompt e Logs."""
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from . import services


class NewPromptDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Novo prompt", transient_for=parent)
        self.set_default_size(480, 380)
        grid = Gtk.Grid(column_spacing=8, row_spacing=8,
                        margin_top=10, margin_bottom=10, margin_start=10, margin_end=10)
        grid.attach(Gtk.Label(label="Trigger (ex: ppcrit):", xalign=1), 0, 0, 1, 1)
        self.trigger = Gtk.Entry()
        grid.attach(self.trigger, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Label:", xalign=1), 0, 1, 1, 1)
        self.label = Gtk.Entry()
        grid.attach(self.label, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Prompt (corpo):", xalign=1, valign=Gtk.Align.START),
                    0, 2, 1, 1)
        self.body = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.body.set_size_request(-1, 180)
        sc = Gtk.ScrolledWindow()
        sc.add(self.body)
        grid.attach(sc, 1, 2, 1, 1)
        err = Gtk.Label(xalign=0)
        err.get_style_context().add_class("stat")
        self._err = err
        grid.attach(err, 1, 3, 1, 1)
        self.get_content_area().pack_start(grid, True, True, 0)
        self.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        self.add_button("Salvar + reload espanso", Gtk.ResponseType.OK)
        self.show_all()

    def save(self) -> str:
        buf = self.body.get_buffer()
        body = buf.get_text(*buf.get_bounds(), True).strip()
        trigger = self.trigger.get_text().strip()
        label = self.label.get_text().strip() or trigger
        if not trigger or not body:
            return "trigger e corpo obrigatórios"
        return services.append_prompt(trigger, label, body)


class LogsDialog(Gtk.Dialog):
    def __init__(self, parent=None, n: int = 30):
        super().__init__(title="promptech — últimos eventos", transient_for=parent)
        self.set_default_size(560, 320)
        buf = Gtk.TextView()
        buf.get_buffer().set_text(services.tail_log(n))
        buf.set_left_margin(8)
        sc = Gtk.ScrolledWindow()
        sc.add(buf)
        self.get_content_area().pack_start(sc, True, True, 0)
        self.add_button("Fechar", Gtk.ResponseType.CLOSE)
        self.show_all()
