#!/usr/bin/env python3
"""Promptech command center — floating always-on-top overlay (Wayland/KWin)."""
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QProcess


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("promptech")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen.width() - 84, 180, 68, 240)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 12, 10, 12)
        lay.setSpacing(10)
        actions = [
            ("🎙", "Ditado (heard)", "/home/lermf/bin/dictate-heard.sh"),
            ("🔍", "Prompt search", "espanso cmd search"),
            ("⌨", "Ditado local (whisper)", "/home/lermf/bin/dictate-whisper.sh"),
        ]
        for icon, tip, cmd in actions:
            b = QPushButton(icon)
            b.setFixedSize(46, 46)
            b.setToolTip(tip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton{border:1px solid #33507f;border-radius:11px;"
                "font-size:20px;background:transparent;color:#dce7ff}"
                "QPushButton:hover{background:#1d3050}")
            b.clicked.connect(lambda _, c=cmd: self.run(c))
            lay.addWidget(b)
        lay.addStretch(1)

    def run(self, cmd):
        QProcess.startDetached("bash", ["-c", cmd])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QColor(13, 20, 36, 235))
        p.setPen(QColor("#2a3b5c"))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 14, 14)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    overlay = Overlay()
    overlay.show()
    sys.exit(app.exec())
