# command_preview_dialog.py
# Podgląd dokładnej komendy, jaką kolejka uruchomi dla zadania (bez uruchamiania).

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
                             QPushButton, QApplication)
from PyQt6.QtGui import QFontDatabase


class CommandPreviewDialog(QDialog):
    def __init__(self, steps, parent=None):
        """steps: lista (opis_kroku, komenda_tekst) z ProcessManager.build_command_preview()."""
        super().__init__(parent)
        self.setWindowTitle("Podgląd komendy")
        self.resize(900, 450)
        if parent:
            self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Dokładnie te komendy uruchomi kolejka dla tego zadania. "
            "Możesz je skopiować i odpalić ręcznie w terminalu."))

        mono = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self._commands = []
        for label, command in steps:
            layout.addWidget(QLabel(f"<b>{label}</b>"))
            row = QHBoxLayout()
            edit = QPlainTextEdit(command)
            edit.setReadOnly(True)
            edit.setFont(mono)
            row.addWidget(edit)
            copy_btn = QPushButton("Kopiuj")
            copy_btn.clicked.connect(lambda _, c=command, b=copy_btn: self._copy(c, b))
            row.addWidget(copy_btn)
            layout.addLayout(row)
            self._commands.append(command)

        buttons = QHBoxLayout()
        buttons.addStretch()
        if len(self._commands) > 1:
            copy_all = QPushButton("Kopiuj wszystkie")
            copy_all.clicked.connect(lambda: self._copy("\n".join(self._commands), copy_all))
            buttons.addWidget(copy_all)
        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    @staticmethod
    def _copy(text, button):
        QApplication.clipboard().setText(text)
        button.setText("Skopiowano ✓")
