#!/usr/bin/env python3
"""promptech command center v3 — GTK3, Hermes-inspirado.

Painéis: lista de prompts (busca live) + ações laterais.
Recursos: salvar prompt em espanso base.yml (backup auto), copiar p/ clipboard,
abrir espanso search, ditado heard/whisper, revisar config, logs recentes, stats.
~15MB RAM. Requer: GTK3, python3-gobject.
"""
import os
import re
import subprocess
import datetime
import tempfile
import fcntl

os.environ.setdefault("GDK_BACKEND", "wayland")
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gtk

_HOME = os.path.expanduser("~")
BASE_YML = os.path.join(_HOME, ".config/espanso/match/base.yml")
BACKUP_DIR = os.path.join(_HOME, ".config/espanso/backup")
LOG_FILE = os.path.join(_HOME, ".local/state/promptech.log")
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


def log(msg: str) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')}\t{msg}\n")
    except OSError:
        pass


def notify(title: str, body: str = "") -> None:
    try:
        subprocess.run(["notify-send", "-t", "2500", title, body], timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _yaml_unquote(s: str) -> str:
    """Desfaz quoting YAML: '...' com '' dobrado, ou "..."."""
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1]
    return s


def parse_base_yml(path: str):
    """Extrai (trigger, label) pares sem depender de PyYAML (indent-based, leve)."""
    items = []
    try:
        with open(path, encoding="utf-8") as f:
            trigger = label = None
            for line in f:
                s = line.strip()
                if s.startswith("- trigger:"):
                    trigger = _yaml_unquote(s.split(":", 1)[1])
                elif s.startswith("label:"):
                    label = _yaml_unquote(s.split(":", 1)[1])
                elif trigger is not None and label is not None:
                    items.append((trigger, label))
                    trigger = label = None
            if trigger is not None:
                items.append((trigger, label or trigger))
    except OSError:
        pass
    return items


def _base_yml() -> str:
    """Caminho efetivo do base.yml (hook de teste via env)."""
    return os.environ.get("PROMPTECH_BASE_YML") or BASE_YML


def _yaml_quote(s: str) -> str:
    """Single-quote YAML-safe: ' -> ''."""
    return "'" + s.replace("'", "''") + "'"


LOCK_FILE = os.path.join(_HOME, ".local/state/promptech.lock")


def append_prompt(trigger: str, label: str, body: str) -> str:
    """Adiciona prompt ao base.yml: flock -> backup rotativo -> write atômico. Retorna erro ou ''."""
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", trigger):
        return "trigger inválido: use [a-zA-Z0-9_-]+"
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    target = _base_yml()
    os.makedirs(os.path.dirname(target), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    block = (
        f"  - trigger: {_yaml_quote(trigger)}\n"
        f"    label: {_yaml_quote(label or trigger)}\n"
        f"    replace: |\n"
    )
    for ln in body.splitlines() or [""]:
        block += f"      {ln}\n"
    try:
        with open(LOCK_FILE, "w") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                if os.path.exists(target):
                    content = open(target, encoding="utf-8").read()
                    bak = os.path.join(BACKUP_DIR, f"base-{stamp}.yml")
                    with open(bak, "w", encoding="utf-8") as b:
                        b.write(content)
                else:
                    content = "matches:\n"
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".yml")
                with os.fdopen(fd, "w", encoding="utf-8") as t:
                    t.write(content.rstrip("\n") + "\n" + block)
                    t.flush()
                    os.fsync(t.fileno())
                os.replace(tmp, target)  # atômico
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        return str(e)
    # rotação de backups (mantém 5 mais recentes)
    backups = sorted(
        (os.path.join(BACKUP_DIR, p) for p in os.listdir(BACKUP_DIR)),
        key=os.path.getmtime,
    )
    for old in backups[:-5]:
        try:
            os.remove(old)
        except OSError:
            pass
    try:
        subprocess.run(["espanso", "restart"], timeout=5, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        log(f"espanso restart falhou pós-save trigger={trigger}")
    log(f"save trigger={trigger}")
    return ""


class PromptRow(Gtk.ListBoxRow):
    def __init__(self, trigger: str, label: str):
        super().__init__()
        self.trigger, self.label = trigger, label
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        t = Gtk.Label(xalign=0)
        t.set_markup(f"<b>{trigger}</b>  <span foreground='#6f83ad'>{urllib.parse.quote(label)[:40]}</span>")
        box.pack_start(t, False, False, 0)
        self.add(box)


class CommandCenter(Gtk.Window):
    def __init__(self):
        super().__init__(title="promptech")
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(520, 400)
        self.set_position(Gtk.WindowPosition.CENTER)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       margin_top=10, margin_bottom=8, margin_start=10, margin_end=10)
        root.get_style_context().add_class("root")

        # Header
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(xalign=0)
        title.get_style_context().add_class("title")
        title.set_markup("⚡ promptech <span foreground='#6f83ad' size='larger'>command center</span>")
        head.pack_start(title, True, True, 0)
        close = Gtk.Button(label="✕")
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.connect("clicked", lambda *_: Gtk.main_quit())
        head.pack_end(close, False, False, 0)
        head_ev = Gtk.EventBox()
        head_ev.add(head)
        head_ev.connect("button-press-event", self._on_header_drag)
        root.pack_start(head_ev, False, False, 0)

        # Busca global
        self.search = Gtk.SearchEntry()
        self.search.set_name("search-entry")
        self.search.set_placeholder_text("Buscar prompt… (digita p/ filtrar)")
        self.search.connect("search-changed", self._filter)
        self.search.connect("activate", self._copy_first)
        root.pack_start(self.search, False, False, 0)

        # Corpo: lista + ações
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        root.pack_start(body, True, True, 0)

        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self._copy_row)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(280, 240)
        scroll.add(self.listbox)
        left.pack_start(scroll, True, True, 0)
        body.pack_start(left, True, True, 0)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        actions = [
            ("🎙  Ditado heard", f"{_HOME}/bin/dictate-heard.sh"),
            ("⌨  Ditado whisper", f"{_HOME}/bin/dictate-whisper.sh"),
            ("🔍  Espanso search", "espanso cmd search"),
            ("➕  Novo prompt", self._new_prompt),
            ("✎  Revisar base.yml", f"xdg-open {_base_yml()}"),
            ("📄  Logs", self._show_logs),
        ]
        for label, cmd in actions:
            b = Gtk.Button(label=label)
            b.get_style_context().add_class("act")
            b.set_tooltip_text(label)
            if callable(cmd):
                b.connect("clicked", lambda _b, fn=cmd: fn())
            else:
                b.connect("clicked", lambda _b, c=cmd: self._spawn(c))
            right.pack_start(b, False, False, 0)
        body.pack_start(right, False, False, 0)

        # Status bar
        self.stat = Gtk.Label(xalign=0)
        self.stat.get_style_context().add_class("stat")
        root.pack_start(self.stat, False, False, 0)

        self.add(root)
        self.reload()

        # ESC fecha
        self.connect("key-press-event", self._on_key)

    # ----- prompts -----
    def reload(self):
        for c in self.listbox.get_children():
            self.listbox.remove(c)
        self._all = parse_base_yml(_base_yml())
        for trigger, label in self._all:
            self.listbox.add(PromptRow(trigger, label))
        self.listbox.show_all()
        n = len(self._all)
        try:
            with open("/proc/uptime") as f:
                up = int(float(f.read().split()[0]) // 3600)
        except OSError:
            up = "?"
        try:
            esp = subprocess.run(["espanso", "status"], capture_output=True, text=True,
                                 check=False, timeout=2).stdout.strip() or "?"
        except (OSError, subprocess.TimeoutExpired):
            esp = "?"
        self.stat.set_markup(
            f"{n} prompts · espanso: {esp} · uptime {up}h · {LOG_FILE.split('/')[-1]}")

    def _filter(self, _e):
        q = self.search.get_text().lower()
        for row in self.listbox.get_children():
            hay = (row.trigger + " " + row.label).lower()
            row.set_visible(q in hay)

    def _visible_rows(self):
        return [r for r in self.listbox.get_children() if r.get_visible()]

    def _copy_row(self, _lb, row):
        try:
            with open(_base_yml(), encoding="utf-8") as f:
                content = f.read()
        except OSError:
            return
        # pega bloco do trigger e extrai 'replace:' literal
        grab, out = False, []
        for line in content.splitlines():
            s = line.strip()
            if s.startswith("- trigger:") and f'"{row.trigger}"' in s:
                grab = True
                continue
            elif grab and s.startswith("- trigger:"):
                break
            if grab and ("replace:" in s or (out and s and not s.startswith(("label:", "vars:", "- name:", "type:", "params:", "layout:")))):
                if "replace:" in s:
                    rest = s.split("replace:", 1)[1].strip()
                    if rest.startswith(("|", ">")):
                        continue
                    if rest:
                        out.append(rest)
                    continue
                out.append(s)
        text = "\n".join(out) or row.trigger
        cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        cb.set_text(text, -1)
        cb.store()
        notify("promptech", f"copiado: {row.trigger}")
        log(f"copy trigger={row.trigger}")

    def _copy_first(self, *_a):
        rows = self._visible_rows()
        if rows:
            self.listbox.select_row(rows[0])
            self._copy_row(self.listbox, rows[0])
            Gtk.main_quit()

    def _spawn(self, cmd: str):
        try:
            subprocess.run(["bash", "-c", cmd], timeout=10, check=False)
        except (OSError, subprocess.TimeoutExpired) as e:
            notify("promptech", f"spawn falhou: {e}")
        log(f"spawn: {cmd[:60]}")

    def _new_prompt(self):
        dlg = NewPromptDialog(self)
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.OK:
            self.reload()

    def _show_logs(self):
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                lines = f.read().splitlines()[-30:]
            text = "\n".join(lines) or "(log vazio)"
        except OSError:
            text = "(sem log ainda)"
        dlg = Gtk.Dialog(title="promptech — últimos eventos")
        dlg.set_default_size(560, 320)
        buf = Gtk.TextView()
        buf.get_buffer().set_text(text)
        buf.set_left_margin(8)
        sc = Gtk.ScrolledWindow()
        sc.add(buf)
        dlg.get_content_area().pack_start(sc, True, True, 0)
        dlg.add_button("Fechar", Gtk.ResponseType.CLOSE)
        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def _on_key(self, _w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

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
        grid.attach(Gtk.Label(label="Prompt ( corpo ):", xalign=1, valign=Gtk.Align.START), 0, 2, 1, 1)
        self.body = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.body.set_size_request(-1, 180)
        sc = Gtk.ScrolledWindow()
        sc.add(self.body)
        grid.attach(sc, 1, 2, 1, 1)
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
        return append_prompt(trigger, label, body)



if __name__ == "__main__":
    css = Gtk.CssProvider()
    css.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    win = CommandCenter()
    win.show_all()
    win.search.grab_focus()
    log("open command-center")
    Gtk.main()
