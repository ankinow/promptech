# Instalação (Arch/CachyOS, KDE Wayland)
pacman -S whisper-cpp wl-clipboard ydotool; paru -S espanso  # espanso-wayland
systemctl --user enable --now ydotoold
espanso service register && espanso start
cp config/espanso/* -> ~/.config/espanso/{config/default.yml,match/base.yml}
cp scripts/dictate-whisper.sh ~/bin/
Modelo: curl -o ~/.models/ggml-large-v3-turbo-q5.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin

## Uso
- Digite `pptrad`, `ppresumo`, `ppreview` em qualquer app -> prompt expande (Form para preencher)
- F8 (shortcut KWin) -> ditado toggle: grava -> whisper.cpp PT-BR -> cola na janela focada
- Search bar: Alt+Shift+Space (evita conflito Meta+Space do KDE)

## Pitfalls descobertos (Wayland/KWin)
1. Triggers NÃO podem ter ':' — uinput scancode US vira 'Ç' no layout BR. Use alfanumérico.
2. Form multiline quebra render ("nested name missing") — usar layout single-line + {{var.var}} se precisar.
3. xdotool morto em Wayland — injeção via ydotool(uinput)+wl-copy.
4. Teste E2E precisa Salvar o arquivo p/ ler conteúdo (buffer ≠ disco).
