# component_selection_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
                             QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
                             QDialogButtonBox, QMessageBox, QHBoxLayout,
                             QToolButton, QStyle, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
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
        self.script1_radio = QRadioButton("CPU (CRF)")
        self.script2_radio = QRadioButton("GPU (Nvidia, Bitrate)")
        self.script1_radio.setChecked(True)
        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1)
        self.script_button_group.addButton(self.script2_radio, 2)
        self.script_button_group.buttonClicked.connect(self.update_ui) # Zmienione z toggled

        self.layout.addWidget(self.ffmpeg_script_label)
        self.layout.addWidget(self.script1_radio)
        self.layout.addWidget(self.script2_radio)

        # Sekcja GPU Bitrate
        self.bitrate_label = QLabel("Bitrate (Mbps):", self)
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

        help_button = QToolButton(self)
        help_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        help_button.clicked.connect(self.show_import_help_dialog)

        import_layout = QHBoxLayout()
        import_layout.addWidget(self.import_button)
        import_layout.addWidget(help_button)

        self.layout.addLayout(import_layout)

        # Sekcja Dialog buttons
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

    def show_import_help_dialog(self):
        help_text = """
        <h4>Format pliku TXT do importu zadań</h4>
        <p>Plik powinien zawierać jedno zadanie w każdej linii. Pola w linii muszą być oddzielone średnikiem (<b>;</b>).</p>
        <p><b>Wymagane jest 8 pól w następującej kolejności:</b></p>
        <ol>
            <li>Pełna ścieżka do pliku wideo (MKV)</li>
            <li>Pełna ścieżka do pliku napisów (.ass)</li>
            <li>Pełna ścieżka do folderu z czcionkami</li>
            <li>Typ skryptu (1, 2, 3 lub 4)</li>
            <li>Typ enkodera FFmpeg (1=CPU, 2=GPU)</li>
            <li>Bitrate (np. 8, 12)</li>
            <li>Tryb debugowania (true lub false)</li>
            <li>Pełna ścieżka do pliku wstawki (intro)</li>
        </ol>
        <p><b>Ważne:</b></p>
        <ul>
            <li>Jeśli któreś pole nie jest używane (np. napisy dla opcji 1 lub bitrate dla CPU), zostaw je puste, ale zachowaj średniki (np. <code>...;;;...</code>).</li>
            <li>Linie zaczynające się od znaku <b>#</b> są ignorowane jako komentarze.</li>
        </ul>
        <p><b>Przykład poprawnej linii:</b></p>
        <pre>C:\\video1.mkv;C:\\napisy1.ass;C:\\fonts;2;2;15;false;</pre>
        """
        QMessageBox.information(self, "Pomoc - Format pliku TXT", help_text)

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
        ffmpeg_encoder_id = self.script_button_group.checkedId()

        needs_subtitles = selected_id in [2, 3]
        needs_intro = selected_id == 4

        self.subtitle_label.setEnabled(needs_subtitles)
        self.subtitle_button.setEnabled(needs_subtitles)
        self.font_label.setEnabled(needs_subtitles)
        self.font_button.setEnabled(needs_subtitles)

        self.intro_label.setEnabled(needs_intro)
        self.intro_button.setEnabled(needs_intro)

        # POPRAWKA: Włącz wybór enkodera tylko dla skryptów 1 i 2
        ffmpeg_encoder_options_enabled = selected_id in [1, 2]
        self.ffmpeg_script_label.setEnabled(ffmpeg_encoder_options_enabled)
        self.script1_radio.setEnabled(ffmpeg_encoder_options_enabled)
        self.script2_radio.setEnabled(ffmpeg_encoder_options_enabled)

        # POPRAWKA: Bitrate jest potrzebny tylko dla GPU (w skryptach 1 i 2) lub zawsze dla skryptu 4
        is_gpu_selected = ffmpeg_encoder_options_enabled and ffmpeg_encoder_id == 2
        is_intro_script = selected_id == 4
        bitrate_is_relevant = is_gpu_selected or is_intro_script

        self.bitrate_label.setEnabled(bitrate_is_relevant)
        self.bitrate_spinbox.setEnabled(bitrate_is_relevant)

    def import_from_txt(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z zadaniami", "", "Text Files (*.txt);;All Files (*)")
        if not file_path: return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się otworzyć pliku: {e}")
            return

        valid_tasks, ignorable_warnings, fatal_errors = [], [], []

        for i, line in enumerate(lines):
            line_num = i + 1
            line_content = line.strip()
            if not line_content or line_content.startswith('#'): continue

            parts = [p.strip() for p in line_content.split(';')]
            if len(parts) != 8:
                fatal_errors.append(f"Linia {line_num}: Niepoprawna liczba pól (oczekiwano 8, otrzymano {len(parts)}).")
                continue

            mkv_path_str, sub_path_str, font_path_str, script_str, ffmpeg_str, bitrate_str, debug_str, intro_path_str = parts

            try:
                script_type = int(script_str) if script_str else 0
                ffmpeg_type = int(ffmpeg_str) if ffmpeg_str else 0
                bitrate = int(bitrate_str) if bitrate_str else 0
                debug = debug_str.lower() in ['true', '1', 'tak']
            except ValueError:
                fatal_errors.append(f"Linia {line_num}: Błędny format danych (typ skryptu/ffmpeg lub bitrate muszą być liczbami).")
                continue

            # --- NOWA, POPRAWIONA WALIDACJA LOGICZNA ---
            line_errors = []
            if script_type in [1, 2]: # Skrypty wymagające wyboru enkodera
                if ffmpeg_type not in [1, 2]:
                    line_errors.append("Brak lub niepoprawny typ enkodera (oczekiwano 1 dla CPU, 2 dla GPU).")
                if ffmpeg_type == 2 and bitrate <= 0: # Bitrate wymagany tylko dla GPU
                    line_errors.append("Brak lub niepoprawny bitrate dla enkodera GPU (musi być > 0).")
            elif script_type == 4: # Skrypt 4 wymaga tylko bitrate
                if bitrate <= 0:
                    line_errors.append("Brak lub niepoprawny bitrate dla skryptu 4 (musi być > 0).")
            elif script_type != 3: # Jeśli nie jest to też skrypt 3 (remux)
                line_errors.append(f"Nieznany typ skryptu: {script_type}.")

            if line_errors:
                fatal_errors.append(f"Linia {line_num}: " + ", ".join(line_errors))
                continue
            # --- KONIEC NOWEJ WALIDACJI ---

            line_warnings = []
            mkv_path = Path(mkv_path_str)
            if not mkv_path.is_file(): line_warnings.append(f"Plik MKV nie istnieje: '{mkv_path_str}'")

            subtitle_path, font_folder, intro_path = None, None, None
            if script_type in [2, 3]:
                if sub_path_str: subtitle_path = Path(sub_path_str)
                if font_path_str: font_folder = Path(font_path_str)
                if not subtitle_path or not subtitle_path.is_file(): line_warnings.append(f"Plik napisów nie istnieje: '{sub_path_str}'")
                if not font_folder or not font_folder.is_dir(): line_warnings.append(f"Folder czcionek nie istnieje: '{font_path_str}'")
            if script_type == 4:
                if intro_path_str: intro_path = Path(intro_path_str)
                if not intro_path or not intro_path.is_file(): line_warnings.append(f"Plik wstawki nie istnieje: '{intro_path_str}'")

            task_data = (mkv_path, subtitle_path, font_folder, script_type, ffmpeg_type, bitrate, debug, intro_path)
            if not line_warnings:
                valid_tasks.append(task_data)
            else:
                ignorable_warnings.append((f"Linia {line_num}: " + ", ".join(line_warnings), task_data))

        if ignorable_warnings:
            error_dialog = ErrorSelectionDialog(ignorable_warnings, self)
            if error_dialog.exec() == QDialog.DialogCode.Accepted:
                valid_tasks.extend(error_dialog.get_selected_tasks())

        if fatal_errors:
            QMessageBox.critical(self, "Błędy krytyczne", "Wystąpiły krytyczne błędy, które uniemożliwiły import niektórych zadań:\n\n" + "\n".join(fatal_errors))

        if valid_tasks:
            self.batch_tasks = valid_tasks
            QMessageBox.information(self, "Sukces", f"Pomyślnie zaimportowano {len(valid_tasks)} zadań.")
        elif not fatal_errors and not ignorable_warnings:
            QMessageBox.information(self, "Informacja", "Nie znaleziono zadań do zaimportowania w pliku.")

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

class ErrorSelectionDialog(QDialog):
    def __init__(self, warnings_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wykryto problemy - wybierz zadania do dodania")
        self.setMinimumWidth(700)
        self.warnings_data = warnings_data
        layout = QVBoxLayout(self)
        info_label = QLabel("Wykryto potencjalne problemy w poniższych zadaniach.\n"
                          "Zaznacz te, które chcesz mimo wszystko dodać do kolejki.", self)
        layout.addWidget(info_label)
        self.list_widget = QListWidget(self)
        for text, task_data in self.warnings_data:
            item = QListWidgetItem(text, self.list_widget)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, task_data)
        layout.addWidget(self.list_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_tasks(self):
        selected_tasks = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                task_data = item.data(Qt.ItemDataRole.UserRole)
                selected_tasks.append(task_data)
        return selected_tasks
