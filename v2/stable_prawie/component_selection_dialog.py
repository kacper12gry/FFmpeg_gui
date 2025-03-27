from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QRadioButton, QButtonGroup, QSpinBox, QCheckBox, QDialogButtonBox, QMessageBox, QHBoxLayout
from pathlib import Path

class ComponentSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wybierz komponenty")
        self.setGeometry(100, 100, 600, 400)
        self.batch_tasks = []  # Lista zadań z pliku TXT

        self.layout = QVBoxLayout()

        self.mkv_label = QLabel("Plik MKV: Nie wybrano", self)
        self.mkv_button = QPushButton("Wybierz plik MKV", self)
        self.mkv_button.clicked.connect(self.select_mkv_file)
        self.layout.addWidget(self.mkv_label)
        self.layout.addWidget(self.mkv_button)

        self.subtitle_label = QLabel("Plik z napisami: Nie wybrano", self)
        self.subtitle_button = QPushButton("Wybierz plik z napisami", self)
        self.subtitle_button.clicked.connect(self.select_subtitle_file)
        self.layout.addWidget(self.subtitle_label)
        self.layout.addWidget(self.subtitle_button)

        self.font_label = QLabel("Folder z czcionkami: Nie wybrano", self)
        self.font_button = QPushButton("Wybierz folder z czcionkami", self)
        self.font_button.clicked.connect(self.select_font_folder)
        self.layout.addWidget(self.font_label)
        self.layout.addWidget(self.font_button)

        self.ffmpeg_radio = QRadioButton("Użyj tylko FFmpeg")
        self.mkvmerge_radio = QRadioButton("Użyj tylko mkvmerge")
        self.mkvmerge_ffmpeg_radio = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.mkvmerge_ffmpeg_radio.setChecked(True)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.ffmpeg_radio, 1)
        self.button_group.addButton(self.mkvmerge_ffmpeg_radio, 2)
        self.button_group.addButton(self.mkvmerge_radio, 3)

        self.button_group.buttonClicked.connect(self.update_ui)

        self.layout.addWidget(self.ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_radio)

        self.script1_radio = QRadioButton("CPU")
        self.script2_radio = QRadioButton("GPU (Nvidia)")
        self.script1_radio.setChecked(True)

        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1)
        self.script_button_group.addButton(self.script2_radio, 2)

        self.layout.addWidget(QLabel("Wybierz skrypt FFmpeg:"))
        self.layout.addWidget(self.script1_radio)
        self.layout.addWidget(self.script2_radio)

        self.bitrate_label = QLabel("GPU Bitrate (Mbps):", self)
        self.bitrate_spinbox = QSpinBox(self)
        self.bitrate_spinbox.setRange(1, 100)
        self.bitrate_spinbox.setValue(8)
        self.layout.addWidget(self.bitrate_label)
        self.layout.addWidget(self.bitrate_spinbox)

        self.debug_checkbox = QCheckBox("Debug Mode", self)
        self.layout.addWidget(self.debug_checkbox)

        # Nowy przycisk do importu z pliku TXT
        self.import_button = QPushButton("Importuj zadania z pliku TXT", self)
        self.import_button.clicked.connect(self.import_from_txt)
        self.layout.addWidget(self.import_button)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

        self.mkv_file = None
        self.subtitle_file = None
        self.font_folder = None

        # Inicjalizacja UI
        self.update_ui(self.mkvmerge_ffmpeg_radio)

    def select_mkv_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik MKV", "", "MKV Files (*.mkv);;All Files (*)", options=options
        )
        if file_path:
            self.mkv_file = Path(file_path)
            self.mkv_label.setText(f"Plik MKV: {self.mkv_file}")

    def select_subtitle_file(self):
        options = QFileDialog.Options()
        subtitle_file, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)", options=options
        )
        if subtitle_file:
            self.subtitle_file = Path(subtitle_file)
            self.subtitle_label.setText(f"Plik z napisami: {self.subtitle_file}")

    def select_font_folder(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami", options=options)
        if folder_path:
            self.font_folder = Path(folder_path)
            self.font_label.setText(f"Folder z czcionkami: {self.font_folder}")

    def update_ui(self, button):
        if button == self.ffmpeg_radio:
            self.subtitle_label.setDisabled(True)
            self.subtitle_button.setDisabled(True)
            self.font_label.setDisabled(True)
            self.font_button.setDisabled(True)
        else:
            self.subtitle_label.setDisabled(False)
            self.subtitle_button.setDisabled(False)
            self.font_label.setDisabled(False)
            self.font_button.setDisabled(False)

    def import_from_txt(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik z zadaniami", "", "Text Files (*.txt);;All Files (*)", options=options
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się otworzyć pliku: {e}")
                return

            tasks = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue  # Pomijamy puste linie i komentarze
                parts = line.split(';')
                if len(parts) != 7:
                    QMessageBox.warning(self, "Błąd", f"Niepoprawny format linii:\n{line}")
                    continue
                mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode = parts
                try:
                    selected_script = int(selected_script)
                    selected_ffmpeg_script = int(selected_ffmpeg_script)
                    gpu_bitrate = int(gpu_bitrate)
                    debug_mode = debug_mode.strip().lower() in ['true', '1', 'tak']
                except ValueError:
                    QMessageBox.warning(self, "Błąd", f"Błędny format typów w linii:\n{line}")
                    continue

                # Jeśli skrypt 1, ustawiamy None dla subtitle_file i font_folder
                if selected_script == 1:
                    subtitle_file = None
                    font_folder = None

                task = (Path(mkv_file), Path(subtitle_file) if subtitle_file else None,
                        Path(font_folder) if font_folder else None,
                        selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode)
                tasks.append(task)
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
