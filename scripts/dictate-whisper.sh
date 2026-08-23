#!/usr/bin/env bash
# Promptech v2 — Wayland/KWin: toggle F8; whisper.cpp; cola via ydotool (uinput) c/ fallback wtype
set -u
STATE=/tmp/promptech-dictate.pid
WAV=/tmp/promptech-voice.wav
MODEL="${PROMPTECH_MODEL:-$HOME/.models/ggml-large-v3-turbo-q5.bin}"
WHISPER="$(command -v whisper-cli || echo whisper-cli)"

paste() { # $1=texto
  local old
  old=$(wl-paste 2>/dev/null || true)
  printf '%s' "$1" | wl-copy
  sleep 0.15
  if command -v ydotool >/dev/null && pgrep -x ydotoold >/dev/null; then
    ydotool key 29:1 47:1 47:0 29:0   # ctrl+v scancodes
  elif command -v wtype >/dev/null; then
    wtype -M ctrl -k v -m ctrl
  else
    notify-send -u critical "Promptech" "Nem ydotoold nem wtype ativos"; exit 1
  fi
  ( sleep 1.5; printf '%s' "$old" | wl-copy ) &
}

if [[ -f $STATE ]]; then
  PID=$(cat "$STATE")
  kill -INT "$PID" 2>/dev/null && sleep 0.4
  kill -TERM "$PID" 2>/dev/null
  rm -f "$STATE"
  notify-send -t 2000 "Promptech" "Transcrevendo…"
  TEXT=$("$WHISPER" -m "$MODEL" -l pt -nt -np "$WAV" 2>/dev/null | sed '/^\s*$/d')
  if [[ -z ${TEXT:-} ]]; then notify-send -u critical "Promptech" "Transcrição vazia — modelo em $MODEL?"; exit 1; fi
  paste "$TEXT"
  notify-send -t 1500 "Promptech" "Colado ✓"
else
  rm -f "$WAV"
  pw-record --channels=1 --rate=16000 "$WAV" &
  echo $! > "$STATE"
  notify-send -t 2500 "Promptech ● REC" "F8 de novo para parar"
fi
