# component_selection_dialog.py
# ZMIANA: Importy z PyQt6
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
                             QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
                             QDialogButtonBox, QMessageBox, QHBoxLayout)
from pathlib import Path

class ComponentSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wybierz komponenty")
        self.setGeometry(100, 100, 600, 450)
        self.batch_tasks = []

        self.layout = QVBoxLayout()

        # Sekcja MKV File
        self.mkv_label = QLabel("Plik MKV: Nie wybrano", self)
        self.mkv_button = QPushButton("Wybierz plik MKV", self)
        self.mkv_button.clicked.connect(self.select_mkv_file)
        self.layout.addWidget(self.mkv_label)
        self.layout.addWidget(self.mkv_button)

        # Sekcja Intro File
        self.intro_label = QLabel("Plik wstawki (intro): Nie wybrano", self)
        self.intro_button = QPushButton("Wybierz plik wstawki", self)
        self.intro_button.clicked.connect(self.select_intro_file)
        self.layout.addWidget(self.intro_label)
        self.layout.addWidget(self.intro_button)

        # Sekcja Subtitle File
        self.subtitle_label = QLabel("Plik z napisami: Nie wybrano", self)
        self.subtitle_button = QPushButton("Wybierz plik z napisami", self)
        self.subtitle_button.clicked.connect(self.select_subtitle_file)
        self.layout.addWidget(self.subtitle_label)
        self.layout.addWidget(self.subtitle_button)

        # Sekcja Font Folder
        self.font_label = QLabel("Folder z czcionkami: Nie wybrano", self)
        self.font_button = QPushButton("Wybierz folder z czcionkami", self)
        self.font_button.clicked.connect(self.select_font_folder)
        self.layout.addWidget(self.font_label)
        self.layout.addWidget(self.font_button)

        # Sekcja Script type selection
        self.ffmpeg_radio = QRadioButton("Użyj tylko FFmpeg (hardsub)")
        self.mkvmerge_ffmpeg_radio = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.mkvmerge_radio = QRadioButton("Użyj tylko mkvmerge (remux)")
        self.ffmpeg_intro_radio = QRadioButton("FFmpeg + Wstawka (intro)")
        self.mkvmerge_ffmpeg_radio.setChecked(True)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.ffmpeg_radio, 1)
        self.button_group.addButton(self.mkvmerge_ffmpeg_radio, 2)
        self.button_group.addButton(self.mkvmerge_radio, 3)
        self.button_group.addButton(self.ffmpeg_intro_radio, 4)
        self.button_group.buttonClicked.connect(self.update_ui)

        self.layout.addWidget(self.ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_radio)
        self.layout.addWidget(self.ffmpeg_intro_radio)

        # Sekcja FFmpeg script selection (CPU/GPU)
        self.ffmpeg_script_label = QLabel("Wybierz skrypt FFmpeg (dla opcji z FFmpeg):")
        self.script1_radio = QRadioButton("CPU")
        self.script2_radio = QRadioButton("GPU (Nvidia)")
        self.script1_radio.setChecked(True)
        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1)
        self.script_button_group.addButton(self.script2_radio, 2)
        self.script2_radio.toggled.connect(self.update_ui) # Aktualizuj UI przy zmianie GPU/CPU

        self.layout.addWidget(self.ffmpeg_script_label)
        self.layout.addWidget(self.script1_radio)
        self.layout.addWidget(self.script2_radio)

        # Sekcja GPU Bitrate
        self.bitrate_label = QLabel("GPU Bitrate (Mbps):", self)
        self.bitrate_spinbox = QSpinBox(self)
        self.bitrate_spinbox.setRange(1, 100)
        self.bitrate_spinbox.setValue(8)
        self.layout.addWidget(self.bitrate_label)
        self.layout.addWidget(self.bitrate_spinbox)

        # Sekcja Debug
        self.debug_checkbox = QCheckBox("Debug Mode", self)
        self.layout.addWidget(self.debug_checkbox)

        # Sekcja Import
        self.import_button = QPushButton("Importuj zadania z pliku TXT", self)
        self.import_button.clicked.connect(self.import_from_txt)
        self.layout.addWidget(self.import_button)

        # Sekcja Dialog buttons
        # ZMIANA: Użycie enum StandardButton
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

        self.mkv_file = None
        self.subtitle_file = None
        self.font_folder = None
        self.intro_file = None

        self.update_ui()

    def select_mkv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik MKV", "", "MKV Files (*.mkv);;All Files (*)")
        if file_path:
            self.mkv_file = Path(file_path)
            self.mkv_label.setText(f"Plik MKV: {self.mkv_file.name}")

    def select_intro_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik wstawki", "", "Video Files (*.mp4 *.mkv);;All Files (*)")
        if file_path:
            self.intro_file = Path(file_path)
            self.intro_label.setText(f"Plik wstawki: {self.intro_file.name}")

    def select_subtitle_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)")
        if file_path:
            self.subtitle_file = Path(file_path)
            self.subtitle_label.setText(f"Plik z napisami: {self.subtitle_file.name}")

    def select_font_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami")
        if folder_path:
            self.font_folder = Path(folder_path)
            self.font_label.setText(f"Folder z czcionkami: {self.font_folder.name}")

    def update_ui(self):
        selected_id = self.button_group.checkedId()

        needs_subtitles = selected_id in [2, 3]
        needs_intro = selected_id == 4
        needs_ffmpeg_options = selected_id in [1, 2]

        self.subtitle_label.setEnabled(needs_subtitles)
        self.subtitle_button.setEnabled(needs_subtitles)
        self.font_label.setEnabled(needs_subtitles)
        self.font_button.setEnabled(needs_subtitles)

        self.intro_label.setEnabled(needs_intro)
        self.intro_button.setEnabled(needs_intro)

        self.ffmpeg_script_label.setEnabled(needs_ffmpeg_options)
        self.script1_radio.setEnabled(needs_ffmpeg_options)
        self.script2_radio.setEnabled(needs_ffmpeg_options)

        gpu_selected = self.script2_radio.isChecked()
        self.bitrate_label.setEnabled(needs_ffmpeg_options and gpu_selected)
        self.bitrate_spinbox.setEnabled(needs_ffmpeg_options and gpu_selected)

    def import_from_txt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z zadaniami", "", "Text Files (*.txt);;All Files (*)")
        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się otworzyć pliku: {e}")
            return

        tasks = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'): continue

            parts = [p.strip() for p in line.split(';')]
            if len(parts) != 8:
                QMessageBox.warning(self, "Błąd w pliku", f"Niepoprawna liczba pól w linii {i+1} (oczekiwano 8, otrzymano {len(parts)}):\n{line}")
                continue

            mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode, intro_file = parts

            try:
                selected_script = int(selected_script)
                selected_ffmpeg_script = int(selected_ffmpeg_script)
                gpu_bitrate = int(gpu_bitrate)
                debug_mode = debug_mode.lower() in ['true', '1', 'tak']
            except ValueError:
                QMessageBox.warning(self, "Błąd w pliku", f"Błędny format danych liczbowych w linii {i+1}:\n{line}")
                continue

            if selected_script == 4 and not intro_file:
                 QMessageBox.warning(self, "Błąd w pliku", f"Brak ścieżki do wstawki dla zadania typu 4 w linii {i+1}:\n{line}")
                 continue

            tasks.append((Path(mkv_file) if mkv_file else None, Path(subtitle_file) if subtitle_file else None, Path(font_folder) if font_folder else None, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode, Path(intro_file) if intro_file else None))

        if tasks:
            self.batch_tasks = tasks
            QMessageBox.information(self, "Sukces", f"Pomyślnie zaimportowano {len(tasks)} zadań.")
        else:
            QMessageBox.information(self, "Informacja", "Nie znaleziono poprawnych zadań w pliku.")

    @property
    def selected_script(self):
        return self.button_group.checkedId()

    @property
    def selected_ffmpeg_script(self):
        return self.script_button_group.checkedId()

    @property
    def gpu_bitrate(self):
        return self.bitrate_spinbox.value()

    @property
    def debug_mode(self):
        return self.debug_checkbox.isChecked()

