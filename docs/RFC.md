# RFC-001 — Prompt Store + Voice Dictation com Hotkeys Globais

## Request
Operador LERMF precisa de: (A) armazenar/reusar prompts inseríveis em QUALQUER janela via atalho global; (B) voice-to-text que insere texto na janela focada via atalho global. Ambiente: CachyOS, i3, X11, PT-BR, preferência local/offline.

## Decision (research-confirmed 2026-08-22)
- A: **Espanso** (search bar global, Forms [[field]], keyboard_layout br)
- B: **Nerd Dictation** (VOSK push-to-talk) + caminho B2 whisper.cpp large-v3-turbo Q5 para qualidade PT-BR (WER ~4% vs Vosk 33–69%)
- Injeção: xdotool / clipboard+ctrl+v; bindsym --release no i3

## Success criteria (measurable)
1. `espanso status` OK e search bar abre em qualquer janela via hotkey
2. Prompt de exemplo com Form [[field]] expande corretamente em editor qualquer
3. `nerd-dictation begin/end` transcreve fala PT-BR e injeta na janela focada (prova real: texto aparece)
4. bindsyms presentes no i3 config; autostart systemd --user ativo
5. Rollback: desinstalar pacotes + remover bloco marcado do i3 config

## Boundaries
- ALWAYS: backup do i3 config antes de editar; fail-closed se pacote ausente
- ASK: nada (DEV total, doutrina operador)
- NEVER: tocar em outros blocos do i3 config; instalar Flatpak dsnote sem decisão
