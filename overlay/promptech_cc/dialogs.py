"""promptech_cc.dialogs — Novo prompt, Logs e Configurações."""
import os
import subprocess
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from . import services


class NewPromptDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Novo prompt", transient_for=parent)
        self.set_default_size(520, 400)
        grid = Gtk.Grid(column_spacing=10, row_spacing=10,
                        margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        grid.attach(Gtk.Label(label="Trigger (ex: ppcrit):", xalign=1), 0, 0, 1, 1)
        self.trigger = Gtk.Entry()
        self.trigger.set_hexpand(True)
        grid.attach(self.trigger, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Label:", xalign=1), 0, 1, 1, 1)
        self.label = Gtk.Entry()
        self.label.set_hexpand(True)
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
    def __init__(self, parent=None, n: int = 50):
        super().__init__(title="promptech — últimos eventos", transient_for=parent)
        self.set_default_size(680, 420)
        buf = Gtk.TextView()
        buf.set_editable(False)
        buf.set_cursor_visible(False)
        buf.get_buffer().set_text(services.tail_log(n))
        buf.set_left_margin(10)
        buf.set_right_margin(10)
        buf.set_top_margin(10)
        buf.set_bottom_margin(10)
        sc = Gtk.ScrolledWindow()
        sc.add(buf)
        self.get_content_area().pack_start(sc, True, True, 0)
        self.add_button("Fechar", Gtk.ResponseType.CLOSE)
        self.show_all()


class SettingsDialog(Gtk.Dialog):
    """Diálogo completo de configurações e governança do Promptech Command Center."""

    def __init__(self, parent=None):
        super().__init__(title="Configurações · Promptech", transient_for=parent)
        self.set_default_size(680, 480)
        self.settings = services.load_settings()

        notebook = Gtk.Notebook()
        notebook.set_tab_pos(Gtk.PositionType.TOP)

        # Tab 1: Voz / Whisper
        tab_voice = self._build_voice_tab()
        notebook.append_page(tab_voice, Gtk.Label(label="🎙️ Voz / Whisper"))

        # Tab 2: Espanso & Prompts
        tab_espanso = self._build_espanso_tab()
        notebook.append_page(tab_espanso, Gtk.Label(label="⚙️ Espanso & Prompts"))

        # Tab 3: Backups & Atalhos
        tab_backups = self._build_backups_tab()
        notebook.append_page(tab_backups, Gtk.Label(label="💾 Backups & Atalhos"))

        self.get_content_area().pack_start(notebook, True, True, 6)

        self.add_button("Cancelar", Gtk.ResponseType.CANCEL)
        save_btn = self.add_button("Salvar", Gtk.ResponseType.OK)
        save_btn.get_style_context().add_class("suggested-action")

        self.show_all()

    def _build_voice_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                       margin_top=14, margin_bottom=14, margin_start=14, margin_end=14)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)

        # Modelo whisper
        grid.attach(Gtk.Label(label="Modelo Whisper:", xalign=1), 0, 0, 1, 1)
        self.model_combo = Gtk.ComboBoxText.new_with_entry()
        models = services.list_available_models()
        current_model = self.settings.get("whisper_model", "")
        
        # Preencher combobox
        found_current = False
        for m in models:
            self.model_combo.append_text(m)
            if m == current_model:
                self.model_combo.set_active_id(m)
                found_current = True

        entry = self.model_combo.get_child()
        if isinstance(entry, Gtk.Entry):
            entry.set_text(current_model or "~/.models/ggml-base-q5_1.bin")
            entry.set_hexpand(True)

        grid.attach(self.model_combo, 1, 0, 1, 1)

        # Idioma
        grid.attach(Gtk.Label(label="Idioma (código):", xalign=1), 0, 1, 1, 1)
        self.lang_entry = Gtk.Entry()
        self.lang_entry.set_text(self.settings.get("whisper_lang", "pt"))
        self.lang_entry.set_placeholder_text("ex: pt, en, es")
        grid.attach(self.lang_entry, 1, 1, 1, 1)

        # Sample Rate
        grid.attach(Gtk.Label(label="Taxa de amostragem (Hz):", xalign=1), 0, 2, 1, 1)
        self.rate_entry = Gtk.Entry()
        self.rate_entry.set_text(str(self.settings.get("audio_rate", 16000)))
        grid.attach(self.rate_entry, 1, 2, 1, 1)

        # Canais de áudio
        grid.attach(Gtk.Label(label="Canais de áudio:", xalign=1), 0, 3, 1, 1)
        self.channels_entry = Gtk.Entry()
        self.channels_entry.set_text(str(self.settings.get("audio_channels", 1)))
        grid.attach(self.channels_entry, 1, 3, 1, 1)

        vbox.pack_start(grid, False, False, 0)

        # Explicação / Dica
        info = Gtk.Label(xalign=0)
        info.get_style_context().add_class("stat")
        info.set_line_wrap(True)
        info.set_markup(
            "<small><i>Modelos whisper.cpp são detectados em ~/.models, ~/.local/share/whisper ou /usr/share/whisper. "
            "Padrão: 16kHz mono (1 canal).</i></small>"
        )
        vbox.pack_start(info, False, False, 0)

        return vbox

    def _build_espanso_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                       margin_top=14, margin_bottom=14, margin_start=14, margin_end=14)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12)

        # Status Espanso
        grid.attach(Gtk.Label(label="Status do Daemon:", xalign=1), 0, 0, 1, 1)
        st_text = services.espanso_status()
        self.espanso_stat_label = Gtk.Label(xalign=0)
        color = "#a6e3a1" if "ativo" in st_text.lower() or "ok" in st_text.lower() else "#fab387"
        self.espanso_stat_label.set_markup(f"<b><span foreground='{color}'>{st_text}</span></b>")
        grid.attach(self.espanso_stat_label, 1, 0, 1, 1)

        # Arquivo base.yml
        grid.attach(Gtk.Label(label="Arquivo base.yml:", xalign=1), 0, 1, 1, 1)
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        path_lbl = Gtk.Label(label=services.base_yml(), xalign=0, hexpand=True)
        path_lbl.set_ellipsize(3)
        path_box.pack_start(path_lbl, True, True, 0)
        
        btn_open = Gtk.Button(label="✎ Abrir no Editor")
        btn_open.connect("clicked", lambda *_: subprocess.Popen(["xdg-open", services.base_yml()]))
        path_box.pack_start(btn_open, False, False, 0)
        grid.attach(path_box, 1, 1, 1, 1)

        # Reload automático
        self.chk_auto_reload = Gtk.CheckButton(label="Recarregar Espanso automaticamente ao salvar prompts/backups")
        self.chk_auto_reload.set_active(bool(self.settings.get("auto_reload_espanso", True)))
        grid.attach(self.chk_auto_reload, 1, 2, 1, 1)

        vbox.pack_start(grid, False, False, 0)

        # Botão Testar Reload Espanso
        btn_reload = Gtk.Button(label="🔄 Testar Reload Espanso")
        self.reload_feedback = Gtk.Label(xalign=0)
        self.reload_feedback.get_style_context().add_class("stat")

        def _on_test_reload(_b):
            ok = services.restart_espanso()
            status = services.espanso_status()
            if ok:
                self.reload_feedback.set_markup(
                    f"<span foreground='#a6e3a1'>✓ Reload disparado com sucesso! (Status: {status})</span>"
                )
            else:
                self.reload_feedback.set_markup(
                    f"<span foreground='#f38ba8'>✕ Falha ao reiniciar espanso. (Status: {status})</span>"
                )
            self.espanso_stat_label.set_markup(f"<b>{status}</b>")

        btn_reload.connect("clicked", _on_test_reload)
        reload_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        reload_box.pack_start(btn_reload, False, False, 0)
        reload_box.pack_start(self.reload_feedback, True, True, 0)
        vbox.pack_start(reload_box, False, False, 0)

        return vbox

    def _build_backups_tab(self) -> Gtk.Widget:
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=14, margin_bottom=14, margin_start=14, margin_end=14)

        # Seção Atalhos Globais
        hotkeys_box = Gtk.Frame(label=" Atalhos Globais (KDE / Wayland) ")
        hk_grid = Gtk.Grid(column_spacing=16, row_spacing=6,
                           margin_top=8, margin_bottom=8, margin_start=10, margin_end=10)
        
        hotkeys = [
            ("F8", "Gravação e transcrição de voz (push-to-talk / toggle)"),
            ("F9", "Promptech Command Center (overlay principal)"),
            ("Meta + Space", "Busca nativa e injeção do Espanso"),
        ]
        for row_idx, (key, desc) in enumerate(hotkeys):
            lbl_k = Gtk.Label(xalign=0)
            lbl_k.set_markup(f"<b><tt>{key}</tt></b>")
            lbl_d = Gtk.Label(label=desc, xalign=0, hexpand=True)
            hk_grid.attach(lbl_k, 0, row_idx, 1, 1)
            hk_grid.attach(lbl_d, 1, row_idx, 1, 1)
        
        hotkeys_box.add(hk_grid)
        vbox.pack_start(hotkeys_box, False, False, 0)

        # Seção Backups do base.yml
        bk_frame = Gtk.Frame(label=" Backups do base.yml ")
        bk_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                          margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)

        bk_listbox = Gtk.ListBox()
        bk_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        bk_scroll = Gtk.ScrolledWindow()
        bk_scroll.set_size_request(-1, 140)
        bk_scroll.set_vexpand(True)
        bk_scroll.add(bk_listbox)
        bk_vbox.pack_start(bk_scroll, True, True, 0)

        feedback_label = Gtk.Label(xalign=0)
        feedback_label.get_style_context().add_class("stat")

        def _refresh_backups():
            for c in bk_listbox.get_children():
                bk_listbox.remove(c)
            backups = services.list_backups()
            if not backups:
                empty_row = Gtk.ListBoxRow()
                empty_row.add(Gtk.Label(label="(Nenhum backup encontrado)", xalign=0, margin=6))
                bk_listbox.add(empty_row)
            else:
                for bk in backups:
                    row = Gtk.ListBoxRow()
                    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                                   margin_top=4, margin_bottom=4, margin_start=6, margin_end=6)
                    info_lbl = Gtk.Label(xalign=0, hexpand=True)
                    size_kb = bk['size'] / 1024.0
                    info_lbl.set_markup(f"<b>{bk['filename']}</b>  <small>({bk['mtime']} · {size_kb:.1f} KB)</small>")
                    
                    btn_rst = Gtk.Button(label="Restaurar")
                    btn_rst.connect("clicked", lambda _b, p=bk["path"], fn=bk["filename"]: _on_restore(p, fn))
                    
                    hbox.pack_start(info_lbl, True, True, 0)
                    hbox.pack_start(btn_rst, False, False, 0)
                    row.add(hbox)
                    bk_listbox.add(row)
            bk_listbox.show_all()

        def _on_restore(path: str, filename: str):
            err = services.restore_backup(path)
            if err:
                feedback_label.set_markup(f"<span foreground='#f38ba8'>✕ Erro ao restaurar: {err}</span>")
            else:
                feedback_label.set_markup(f"<span foreground='#a6e3a1'>✓ Backup '{filename}' restaurado com sucesso!</span>")
                _refresh_backups()

        _refresh_backups()
        bk_vbox.pack_start(feedback_label, False, False, 0)
        bk_frame.add(bk_vbox)
        vbox.pack_start(bk_frame, True, True, 0)

        return vbox

    def get_form_data(self) -> dict:
        """Coleta dados do formulário."""
        data = dict(self.settings)

        entry = self.model_combo.get_child()
        if isinstance(entry, Gtk.Entry):
            model_val = entry.get_text().strip()
        else:
            model_val = self.model_combo.get_active_text() or ""

        if model_val:
            data["whisper_model"] = model_val

        data["whisper_lang"] = self.lang_entry.get_text().strip() or "pt"
        
        try:
            data["audio_rate"] = int(self.rate_entry.get_text().strip())
        except ValueError:
            data["audio_rate"] = 16000

        try:
            data["audio_channels"] = int(self.channels_entry.get_text().strip())
        except ValueError:
            data["audio_channels"] = 1

        data["auto_reload_espanso"] = bool(self.chk_auto_reload.get_active())
        return data

    def save(self) -> bool:
        """Salva configurações no disco."""
        data = self.get_form_data()
        return services.save_settings(data)
