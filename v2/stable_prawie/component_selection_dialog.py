# component_selection_dialog.py
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
                             QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
                             QDialogButtonBox, QMessageBox, QHBoxLayout,
                             QToolButton, QStyle, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt
from pathlib import Path

class ComponentSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(QApplication.instance().styleSheet())
        self.setWindowTitle("Wybierz komponenty")
        self.setGeometry(100, 100, 600, 450)

        self.batch_tasks = []
        self.mkv_file, self.subtitle_file, self.font_folder, self.intro_file = None, None, None, None

        self._setup_ui()
        self._connect_signals()
        self.update_ui_state()

    def _setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.mkv_label = QLabel("Plik MKV: Nie wybrano", self)
        self.mkv_button = QPushButton("Wybierz plik MKV", self)
        self.intro_label = QLabel("Plik wstawki (intro): Nie wybrano", self)
        self.intro_button = QPushButton("Wybierz plik wstawki", self)
        self.subtitle_label = QLabel("Plik z napisami: Nie wybrano", self)
        self.subtitle_button = QPushButton("Wybierz plik z napisami", self)
        self.font_label = QLabel("Folder z czcionkami: Nie wybrano", self)
        self.font_button = QPushButton("Wybierz folder z czcionkami", self)
        self.ffmpeg_radio = QRadioButton("Użyj tylko FFmpeg (hardsub)")
        self.mkvmerge_ffmpeg_radio = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.mkvmerge_radio = QRadioButton("Użyj tylko mkvmerge (remux)")
        self.ffmpeg_intro_radio = QRadioButton("FFmpeg + Wstawka (intro)")
        self.mkvmerge_ffmpeg_radio.setChecked(True)
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.ffmpeg_radio, 1); self.button_group.addButton(self.mkvmerge_ffmpeg_radio, 2)
        self.button_group.addButton(self.mkvmerge_radio, 3); self.button_group.addButton(self.ffmpeg_intro_radio, 4)
        self.ffmpeg_script_label = QLabel("Wybierz skrypt FFmpeg (dla opcji z FFmpeg):")
        self.script1_radio = QRadioButton("CPU (CRF)"); self.script2_radio = QRadioButton("GPU (Nvidia, Bitrate)")
        self.script1_radio.setChecked(True)
        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1); self.script_button_group.addButton(self.script2_radio, 2)
        self.bitrate_label = QLabel("Bitrate (Mbps):", self)
        self.bitrate_spinbox = QSpinBox(self)
        self.bitrate_spinbox.setRange(1, 100); self.bitrate_spinbox.setValue(8)
        self.debug_checkbox = QCheckBox("Debug Mode", self)
        self.import_button = QPushButton("Importuj zadania z pliku TXT", self)
        self.help_button = QToolButton(self)
        self.help_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        import_layout = QHBoxLayout()
        import_layout.addWidget(self.import_button); import_layout.addWidget(self.help_button)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.layout.addWidget(self.mkv_label); self.layout.addWidget(self.mkv_button)
        self.layout.addWidget(self.intro_label); self.layout.addWidget(self.intro_button)
        self.layout.addWidget(self.subtitle_label); self.layout.addWidget(self.subtitle_button)
        self.layout.addWidget(self.font_label); self.layout.addWidget(self.font_button)
        self.layout.addWidget(self.ffmpeg_radio); self.layout.addWidget(self.mkvmerge_ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_radio); self.layout.addWidget(self.ffmpeg_intro_radio)
        self.layout.addWidget(self.ffmpeg_script_label); self.layout.addWidget(self.script1_radio); self.layout.addWidget(self.script2_radio)
        self.layout.addWidget(self.bitrate_label); self.layout.addWidget(self.bitrate_spinbox)
        self.layout.addWidget(self.debug_checkbox); self.layout.addLayout(import_layout)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def _connect_signals(self):
        self.mkv_button.clicked.connect(self.select_mkv_file)
        self.intro_button.clicked.connect(self.select_intro_file)
        self.subtitle_button.clicked.connect(self.select_subtitle_file)
        self.font_button.clicked.connect(self.select_font_folder)
        self.button_group.buttonClicked.connect(self.update_ui_state)
        self.script_button_group.buttonClicked.connect(self.update_ui_state)
        self.import_button.clicked.connect(self.import_from_txt)
        self.help_button.clicked.connect(self.show_import_help_dialog)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def update_ui_state(self):
        """POPRAWKA: Przywracamy logikę opartą na setEnabled dla stabilnego interfejsu."""
        selected_id = self.button_group.checkedId()
        ffmpeg_encoder_id = self.script_button_group.checkedId()

        # Określamy, które opcje są potrzebne dla danego skryptu
        needs_subtitles = selected_id in [1, 2, 3]
        needs_intro = selected_id == 4
        ffmpeg_encoder_options_enabled = selected_id in [1, 2]
        is_gpu_selected = ffmpeg_encoder_options_enabled and ffmpeg_encoder_id == 2
        bitrate_is_relevant = is_gpu_selected or needs_intro

        # Włączamy lub wyłączamy (wyszarzamy) odpowiednie kontrolki
        self.subtitle_label.setEnabled(needs_subtitles); self.subtitle_button.setEnabled(needs_subtitles)
        self.font_label.setEnabled(needs_subtitles); self.font_button.setEnabled(needs_subtitles)
        self.intro_label.setEnabled(needs_intro); self.intro_button.setEnabled(needs_intro)
        self.ffmpeg_script_label.setEnabled(ffmpeg_encoder_options_enabled)
        self.script1_radio.setEnabled(ffmpeg_encoder_options_enabled); self.script2_radio.setEnabled(ffmpeg_encoder_options_enabled)
        self.bitrate_label.setEnabled(bitrate_is_relevant); self.bitrate_spinbox.setEnabled(bitrate_is_relevant)

        self._validate_inputs()

    def _validate_inputs(self):
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if not ok_button: return
        is_valid = False
        selected_id = self.button_group.checkedId()
        if selected_id in [1, 2, 3]: is_valid = all([self.mkv_file, self.subtitle_file, self.font_folder])
        elif selected_id == 4: is_valid = all([self.mkv_file, self.intro_file])
        ok_button.setEnabled(is_valid)

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
            <li>Jeśli któreś pole nie jest używane, zostaw je puste, ale zachowaj średniki (np. <code>...;;;...</code>).</li>
            <li>Linie zaczynające się od <b>#</b> są ignorowane.</li>
        </ul>
        """
        QMessageBox.information(self, "Pomoc - Format pliku TXT", help_text)

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
            line_num, line_content = i + 1, line.strip()
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
                fatal_errors.append(f"Linia {line_num}: Błędny format danych (liczby).")
                continue
            line_errors = []
            if script_type in [1, 2]:
                if ffmpeg_type not in [1, 2]: line_errors.append("Brak typu enkodera (1=CPU, 2=GPU).")
                if ffmpeg_type == 2 and bitrate <= 0: line_errors.append("Brak bitrate dla GPU.")
            elif script_type == 4:
                if bitrate <= 0: line_errors.append("Brak bitrate dla skryptu 4.")
            elif script_type != 3:
                line_errors.append(f"Nieznany typ skryptu: {script_type}.")
            if line_errors:
                fatal_errors.append(f"Linia {line_num}: " + ", ".join(line_errors))
                continue
            line_warnings, mkv_path = [], Path(mkv_path_str)
            if not mkv_path.is_file(): line_warnings.append(f"Plik MKV nie istnieje: '{mkv_path_str}'")
            subtitle_path, font_folder, intro_path = None, None, None
            if script_type in [1, 2, 3]:
                if sub_path_str: subtitle_path = Path(sub_path_str)
                if font_path_str: font_folder = Path(font_path_str)
                if not subtitle_path or not subtitle_path.is_file(): line_warnings.append(f"Plik napisów nie istnieje: '{sub_path_str}'")
                if not font_folder or not font_folder.is_dir(): line_warnings.append(f"Folder czcionek nie istnieje: '{font_path_str}'")
            if script_type == 4:
                if intro_path_str: intro_path = Path(intro_path_str)
                if not intro_path or not intro_path.is_file(): line_warnings.append(f"Plik wstawki nie istnieje: '{intro_path_str}'")
            task_data = (mkv_path, subtitle_path, font_folder, script_type, ffmpeg_type, bitrate, debug, intro_path)
            if not line_warnings: valid_tasks.append(task_data)
            else: ignorable_warnings.append((f"Linia {line_num}: " + ", ".join(line_warnings), task_data))
        if fatal_errors:
            QMessageBox.critical(self, "Błędy krytyczne", "Wystąpiły krytyczne błędy importu:\n\n" + "\n".join(fatal_errors))
            return
        if ignorable_warnings:
            error_dialog = ErrorSelectionDialog(ignorable_warnings, self)
            if error_dialog.exec() == QDialog.DialogCode.Accepted: valid_tasks.extend(error_dialog.get_selected_tasks())
        if valid_tasks:
            self.batch_tasks = valid_tasks
            QMessageBox.information(self, "Sukces", f"Pomyślnie zaimportowano {len(valid_tasks)} zadań.")
            self.accept()
        elif not fatal_errors and not ignorable_warnings:
            QMessageBox.information(self, "Informacja", "Nie znaleziono zadań do zaimportowania w pliku.")

    def select_mkv_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik MKV", "", "MKV Files (*.mkv)")
        if path: self.mkv_file = Path(path); self.mkv_label.setText(f"Plik MKV: {self.mkv_file.name}"); self._validate_inputs()
    def select_intro_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz wstawkę", "", "Video Files (*.mp4 *.mkv)")
        if path: self.intro_file = Path(path); self.intro_label.setText(f"Plik wstawki: {self.intro_file.name}"); self._validate_inputs()
    def select_subtitle_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz napisy", "", "ASS Files (*.ass)")
        if path: self.subtitle_file = Path(path); self.subtitle_label.setText(f"Plik napisów: {self.subtitle_file.name}"); self._validate_inputs()
    def select_font_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami")
        if path: self.font_folder = Path(path); self.font_label.setText(f"Folder czcionek: {self.font_folder.name}"); self._validate_inputs()

    @property
    def selected_script(self): return self.button_group.checkedId()
    @property
    def selected_ffmpeg_script(self): return self.script_button_group.checkedId()
    @property
    def gpu_bitrate(self): return self.bitrate_spinbox.value()
    @property
    def debug_mode(self): return self.debug_checkbox.isChecked()

class ErrorSelectionDialog(QDialog):
    def __init__(self, warnings_data, parent=None):
        super().__init__(parent)
        self.setStyleSheet(QApplication.instance().styleSheet())
        self.setWindowTitle("Wykryto problemy - wybierz zadania do dodania")
        self.setMinimumWidth(700)
        self.warnings_data = warnings_data
        layout = QVBoxLayout(self)
        info_label = QLabel("Wykryto potencjalne problemy w poniższych zadaniach.\nZaznacz te, które chcesz mimo wszystko dodać do kolejki.", self)
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
                selected_tasks.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_tasks
