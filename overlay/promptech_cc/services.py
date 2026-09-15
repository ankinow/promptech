"""promptech_cc.services — camada de dados (parse, save, status, spawn, settings, backups).

Sem Gtk aqui: funções puras testáveis. Base:
- base.yml  = ~/.config/espanso/match/base.yml (override teste: PROMPTECH_BASE_YML)
- settings  = ~/.config/promptech/settings.json
- lock      = ~/.local/state/promptech.lock    (flock single-writer)
- backups   = ~/.config/espanso/backup/        (rotativo, mantém 5)
"""
import datetime
import fcntl
import json
import os
import re
import subprocess
import tempfile

_HOME = os.path.expanduser("~")
BASE_YML = os.path.join(_HOME, ".config/espanso/match/base.yml")
BACKUP_DIR = os.path.join(_HOME, ".config/espanso/backup")
LOG_FILE = os.path.join(_HOME, ".local/state/promptech.log")
LOCK_FILE = os.path.join(_HOME, ".local/state/promptech.lock")
SETTINGS_FILE = os.path.join(_HOME, ".config/promptech/settings.json")

DEFAULT_SETTINGS = {
    "whisper_model": os.path.expanduser("~/.models/ggml-base-q5_1.bin"),
    "whisper_lang": "pt",
    "audio_rate": 16000,
    "audio_channels": 1,
    "auto_reload_espanso": True,
    "ui_scale": "large",
    "window_width": 960,
    "window_height": 620,
}

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
    cfg = load_settings()
    if cfg.get("auto_reload_espanso", True):
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


def load_settings() -> dict:
    """Carrega configurações do arquivo SETTINGS_FILE com fallback para DEFAULT_SETTINGS."""
    cfg = dict(DEFAULT_SETTINGS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cfg.update(loaded)
        except (OSError, json.JSONDecodeError) as e:
            log(f"load_settings falhou: {e}")
    return cfg


def save_settings(data: dict) -> bool:
    """Salva configurações atomicamente em SETTINGS_FILE com flock."""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(LOCK_FILE, "w") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(SETTINGS_FILE), suffix=".json")
                with os.fdopen(fd, "w", encoding="utf-8") as t:
                    json.dump(data, t, indent=2, ensure_ascii=False)
                    t.write("\n")
                    t.flush()
                    os.fsync(t.fileno())
                os.replace(tmp, SETTINGS_FILE)
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        log("settings salvos com sucesso")
        return True
    except (OSError, TypeError) as e:
        log(f"save_settings falhou: {e}")
        return False


def list_available_models() -> list[str]:
    """Escaneia diretórios padrão e configurações por modelos whisper (*.bin)."""
    models = set()
    dirs = [
        os.path.expanduser("~/.models"),
        "/usr/share/whisper",
        os.path.expanduser("~/.local/share/whisper"),
    ]
    for d in dirs:
        if os.path.isdir(d):
            try:
                for entry in os.listdir(d):
                    if entry.endswith(".bin"):
                        models.add(os.path.join(d, entry))
            except OSError:
                pass
    settings = load_settings()
    custom_model = settings.get("whisper_model")
    if custom_model and os.path.isfile(custom_model):
        models.add(custom_model)
    return sorted(models)


def list_backups() -> list[dict]:
    """Retorna lista de backups existentes em BACKUP_DIR ordenados do mais recente para o mais antigo."""
    res = []
    if not os.path.isdir(BACKUP_DIR):
        return res
    try:
        for f in os.listdir(BACKUP_DIR):
            if f.endswith(".yml") or f.endswith(".yaml"):
                p = os.path.join(BACKUP_DIR, f)
                try:
                    st = os.stat(p)
                    mtime_dt = datetime.datetime.fromtimestamp(st.st_mtime, tz=datetime.timezone.utc)
                    res.append({
                        "filename": f,
                        "path": p,
                        "mtime": mtime_dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "size": st.st_size,
                    })
                except OSError:
                    pass
    except OSError:
        pass
    res.sort(key=lambda x: x["mtime"], reverse=True)
    return res


def restore_backup(filepath: str) -> str | None:
    """Restaura arquivo de backup (caminho completo ou nome de arquivo). Retorna None se ok ou msg de erro."""
    if os.path.isabs(filepath) and os.path.isfile(filepath):
        src = filepath
    else:
        src = os.path.join(BACKUP_DIR, filepath)
    if not os.path.isfile(src):
        return f"Arquivo de backup '{filepath}' não existe"
    target = base_yml()
    stamp = datetime.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    try:
        with open(LOCK_FILE, "w") as lockf:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
            try:
                if os.path.exists(target):
                    content = open(target, encoding="utf-8").read()
                    with open(os.path.join(BACKUP_DIR, f"base-pre-restore-{stamp}.yml"), "w", encoding="utf-8") as b:
                        b.write(content)
                new_content = open(src, encoding="utf-8").read()
                fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), suffix=".yml")
                with os.fdopen(fd, "w", encoding="utf-8") as t:
                    t.write(new_content)
                    t.flush()
                    os.fsync(t.fileno())
                os.replace(tmp, target)
            finally:
                fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)
        cfg = load_settings()
        if cfg.get("auto_reload_espanso", True):
            restart_espanso()
        log(f"restore_backup success from={src}")
        return None
    except OSError as e:
        log(f"restore_backup falhou: {e}")
        return str(e)
