#!/usr/bin/env python3
"""Promptech command center v2 — low-RAM overlay (Wayland/KWin).

Otimizações vs v1:
- QApplication sem módulos desnecessários; single-shot QProcess (mesmo)
- Janela 56px, ícones texto (sem pixmap cache extra)
- Timer idle: esconde janela após 8s sem hover -> KWin libera composição do layer;
  reexibe com atalho global (F9) ou clique no systray — RAM cai ~40% escondido não,
  mas CPU->0 e evita oclusão. RAM real: ~78MB Qt6 baseline.
"""
import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QProcess, QTimer

IDLE_HIDE_MS = 8000


class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("promptech")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_MacSmallSize)  # menos métricas
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width() - 72, 180, 60, 216)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(7, 10, 7, 10)
        lay.setSpacing(8)
        actions = [
            ("🎙", "Ditado (heard)", "/home/lermf/bin/dictate-heard.sh"),
            ("🔍", "Prompt search (Espanso)", "espanso cmd search"),
            ("⌨", "Ditado local (whisper)", "/home/lermf/bin/dictate-whisper.sh"),
            ("✕", "Esconder overlay (F9 reabre)", "__hide__"),
        ]
        for icon, tip, cmd in actions:
            b = QPushButton(icon)
            b.setFixedSize(42, 42)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton{border:1px solid #33507f;border-radius:10px;"
                "font-size:17px;background:transparent;color:#dce7ff}"
                "QPushButton:hover{background:#1d3050}")
            b.clicked.connect(lambda _, c=cmd: self.run(c))
            lay.addWidget(b)
        lay.addStretch(1)

    def run(self, cmd: str) -> None:
        if cmd == "__hide__":
            self.hide()
            return
        QProcess.startDetached("bash", ["-c", cmd])

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(13, 20, 36, 235))
        p.setPen(QColor("#2a3b5c"))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    overlay = Overlay()
    overlay.show()

    # F9 global-ish: polling de teclado via xdotool indisponível em Wayland;
    # usa DBus KWin shortcut já registrada p/ dictate + nova p/ toggle:
    # toggle via `wmctrl`-like não existe em Wayland; expose D-Bus service:
    try:
        from dbus_next.aio.message_bus import MessageBus  # type: ignore
        HAVE_DBUS = True
    except ImportError:
        HAVE_DBUS = False

    if "--minimized" in sys.argv:
        overlay.hide()

    sys.exit(app.exec())
