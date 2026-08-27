"""promptech_cc.services — camada de dados (parse, save, status, spawn).

Sem Gtk aqui: funções puras testáveis. Base:
- base.yml = ~/.config/espanso/match/base.yml (override teste: PROMPTECH_BASE_YML)
- lock     = ~/.local/state/promptech.lock  (flock single-writer)
- backups  = ~/.config/espanso/backup/      (rotativo, mantém 5)
"""
import datetime
import fcntl
import os
import re
import subprocess
import tempfile

_HOME = os.path.expanduser("~")
BASE_YML = os.path.join(_HOME, ".config/espanso/match/base.yml")
BACKUP_DIR = os.path.join(_HOME, ".config/espanso/backup")
LOG_FILE = os.path.join(_HOME, ".local/state/promptech.log")
LOCK_FILE = os.path.join(_HOME, ".local/state/promptech.lock")

_TRIGGER_RE = re.compile(r"[a-zA-Z0-9_-]+")


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


def base_yml() -> str:
    """Caminho efetivo do base.yml (hook de teste via env)."""
    return os.environ.get("PROMPTECH_BASE_YML") or BASE_YML


def _yaml_quote(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _yaml_unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return s[1:-1]
    return s


def parse_base_yml(path: str):
    """Extrai (trigger, label) pares sem depender de PyYAML."""
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


def read_prompt_body(trigger: str) -> str:
    """Extrai corpo 'replace:' do trigger (multilinha seguro via boundaries de '- trigger:')."""
    try:
        with open(base_yml(), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return trigger
    grab, out, in_replace = False, [], False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- trigger:"):
            if grab:
                break
            grab = f"'{trigger}'" in stripped or f'"{trigger}"' in stripped
            in_replace = False
            continue
        if not grab:
            continue
        if stripped.startswith("replace:"):
            rest = stripped.split("replace:", 1)[1].strip()
            if rest.startswith(("|", ">")):
                in_replace = True
                continue
            if rest:
                out.append(rest)
            continue
        if in_replace and line.startswith(" " * 6):  # corpo indentado sob replace: |
            out.append(stripped)
        elif stripped and not stripped.startswith(("label:", "vars:", "- name:", "type:", "params:", "layout:")) and out is not None:
            # linha solta (replace inline antigo) — só se ainda sem corpo em replace
            if not in_replace:
                out.append(stripped)
    return "\n".join(out) or trigger


def append_prompt(trigger: str, label: str, body: str) -> str:
    """flock -> backup rotativo -> write atômico -> espanso restart. Retorna erro ou ''."""
    if not _TRIGGER_RE.fullmatch(trigger):
        return "trigger inválido: use [a-zA-Z0-9_-]+"
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    target = base_yml()
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
                    with open(os.path.join(BACKUP_DIR, f"base-{stamp}.yml"), "w", encoding="utf-8") as b:
                        b.write(content)
                else:
                    content = "matches:\n"
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".yml")
                with os.fdopen(fd, "w", encoding="utf-8") as t:
                    t.write(content.rstrip("\n") + "\n" + block)
                    t.flush()
                    os.fsync(t.fileno())
                os.replace(tmp, target)
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
    except OSError as e:
        return str(e)
    # rotação: mantém 5 mais recentes
    backups = sorted((os.path.join(BACKUP_DIR, p) for p in os.listdir(BACKUP_DIR)),
                     key=os.path.getmtime)
    for old in backups[:-5]:
        try:
            os.remove(old)
        except OSError:
            pass
    restart_espanso()
    log(f"save trigger={trigger}")
    return ""


def restart_espanso() -> bool:
    try:
        subprocess.run(["espanso", "restart"], timeout=5, check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.TimeoutExpired):
        log("espanso restart falhou")
        return False


def espanso_status() -> str:
    try:
        r = subprocess.run(["espanso", "status"], capture_output=True, text=True,
                           check=False, timeout=2)
        return (r.stdout.strip() or "?").splitlines()[-1]
    except (OSError, subprocess.TimeoutExpired):
        return "?"


def uptime_hours():
    try:
        with open("/proc/uptime") as f:
            return int(float(f.read().split()[0]) // 3600)
    except (OSError, ValueError):
        return None


def run_action(cmd: list, timeout: int = 10) -> str:
    """Ações rápidas síncronas; retorna '' ok ou msg de erro."""
    try:
        subprocess.run(cmd, timeout=timeout, check=False)
        return ""
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"action falhou: {' '.join(cmd)}: {e}")
        return str(e)


def tail_log(n: int = 30) -> str:
    try:
        with open(LOG_FILE, encoding="utf-8") as f:
            return "\n".join(f.read().splitlines()[-n:]) or "(log vazio)"
    except OSError:
        return "(sem log ainda)"
