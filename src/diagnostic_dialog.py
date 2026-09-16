import platform
import shutil
from PyQt6.QtCore import QProcess, Qt
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QGridLayout, QLabel,
                             QPushButton, QMessageBox, QDialogButtonBox, QFrame)

class DiagnosticDialog(QDialog):
    """
    Okno dialogowe, które jednocześnie zarządza diagnostyką i wyświetla jej wyniki.
    """
    def __init__(self, output_window, plugin_manager, parent=None):
        super().__init__(parent)
        self.output_window = output_window
        self.plugin_manager = plugin_manager # Przechowujemy referencję do managera
        self.process = None
        self.setStyleSheet(QApplication.instance().styleSheet())
        self.setWindowTitle("Diagnostyka Programu")
        self.setMinimumWidth(450)
        self.layout = QVBoxLayout(self)
        self.grid_layout = QGridLayout()
        self.results = self.check_dependencies()
        self.is_windows = platform.system() == "Windows"

        self._setup_ui()
        self._setup_dlc_ui() # <-- NOWA METODA DO TWORZENIA SEKCJI DLC

        self.layout.addLayout(self.grid_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def _setup_ui(self):
        """Tworzy interfejs na podstawie wyników diagnostyki zależności."""
        dependencies = {
            "ffmpeg": ("FFmpeg",),
            "mkvmerge": ("MKVToolNix",),
            "ffprobe": ("FFprobe",),
        }
        row = 0
        for key, (name,) in dependencies.items():
            label = QLabel(f"{name}:")
            status_label = QLabel()
            install_button = QPushButton("Instaluj")
            if self.results[key]:
                status_label.setText("✅ Znaleziono")
                status_label.setStyleSheet("color: #4CAF50;") # Zielony
                install_button.setVisible(False)
            else:
                status_label.setText("❌ Nie znaleziono")
                status_label.setStyleSheet("color: #F44336;") # Czerwony
                install_button.setVisible(self.is_windows)

            if key == "ffmpeg":
                install_button.clicked.connect(self.install_ffmpeg_winget)
            elif key == "mkvmerge":
                install_button.clicked.connect(self.show_mkvtoolnix_instructions)

            if key == "ffprobe":
                install_button.setVisible(False)

            self.grid_layout.addWidget(label, row, 0)
            self.grid_layout.addWidget(status_label, row, 1)
            self.grid_layout.addWidget(install_button, row, 2)
            row += 1

    def _setup_dlc_ui(self):
        """Tworzy sekcję interfejsu dla wykrytych dodatków."""
        plugins = self.plugin_manager.get_plugins()
        if not plugins:
            return # Jeśli nie ma pluginów, nic nie rób

        # Dodaj separator wizualny
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.grid_layout.addWidget(separator, self.grid_layout.rowCount(), 0, 1, 3)

        # Dodaj etykietę sekcji
        dlc_header_label = QLabel("Wykryte Dodatki (DLC):")
        dlc_header_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.grid_layout.addWidget(dlc_header_label, self.grid_layout.rowCount(), 0, 1, 3)

        # Dodaj listę wykrytych dodatków
        for plugin in plugins:
            row = self.grid_layout.rowCount()
            name_label = QLabel(plugin['name'])
            # Dodajemy tooltip z dodatkowymi informacjami
            tooltip_text = (f"Autor: {plugin['author']}\n"
                            f"Wersja: {plugin['version']}\n"
                            f"Opis: {plugin['description']}")
            name_label.setToolTip(tooltip_text)

            status_label = QLabel("✅ Wykryto")
            status_label.setStyleSheet("color: #4CAF50;")

            self.grid_layout.addWidget(name_label, row, 0)
            self.grid_layout.addWidget(status_label, row, 1)

    def check_dependencies(self):
        return {
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "mkvmerge": shutil.which("mkvmerge") is not None,
            "ffprobe": shutil.which("ffprobe") is not None,
        }

    def install_ffmpeg_winget(self):
        reply = QMessageBox.information(self, "Instalacja FFmpeg",
            "Aplikacja spróbuje zainstalować FFmpeg za pomocą menedżera pakietów Winget.\n\n"
            "System może poprosić o uprawnienia administratora. Kontynuować?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            program = "winget"
            arguments = ["install", "--id=Gyan.FFmpeg", "-e", "--accept-source-agreements"]
            if self.output_window:
                self.output_window.append(">>> Rozpoczynam instalację FFmpeg przez Winget...")
            self._start_installation_process(program, arguments)
            QMessageBox.information(self, "Informacja", "Rozpoczęto instalację FFmpeg. Sprawdź postęp w głównym oknie w zakładce logów.")
            self.close()

    def show_mkvtoolnix_instructions(self):
        instructions = """
        <h3>Instalacja MKVToolNix</h3>
        <p>Automatyczna instalacja MKVToolNix nie jest zalecana. Aby program działał poprawnie, zainstaluj go ręcznie i upewnij się, że został dodany do ścieżki systemowej (PATH).</p>
        <ol>
            <li>Pobierz instalator ze strony: <b>mkvtoolnix.download</b></li>
            <li>Uruchom instalator.</li>
            <li>W trakcie instalacji, na ekranie "Wybierz komponenty", upewnij się, że opcja <b>"Dodaj do ścieżki systemowej (PATH)"</b> jest zaznaczona.</li>
            <li>Zakończ instalację.</li>
            <li>Uruchom ponownie program, aby wykrył zmiany.</li>
        </ol>
        """
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Instrukcja instalacji MKVToolNix")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(instructions)
        msg_box.exec()
        self.close()

    def _start_installation_process(self, program, arguments):
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        if self.output_window:
            self.process.readyRead.connect(self._update_output)
            self.process.finished.connect(lambda: self.output_window.append(">>> Proces instalacji zakończony."))
        self.process.start(program, arguments)

    def _update_output(self):
        if self.output_window and self.process:
            output = bytes(self.process.readAll()).decode('utf-8', errors='ignore')
            self.output_window.append(output)

