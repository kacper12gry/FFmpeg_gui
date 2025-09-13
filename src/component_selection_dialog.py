import os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
                             QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
                             QDialogButtonBox, QMessageBox, QHBoxLayout, QLineEdit,
                             QToolButton, QStyle, QListWidget, QListWidgetItem, QTabWidget, QWidget, QGroupBox,
                             QComboBox)
from PyQt6.QtCore import Qt, QSettings

class ComponentSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(QApplication.instance().styleSheet())
        self.setWindowTitle("Wybierz Komponenty")
        self.setGeometry(100, 100, 650, 650)
        self.setAcceptDrops(True)
        self.settings = QSettings("settings.ini", QSettings.Format.IniFormat)
        self.batch_tasks = []
        self.mkv_file, self.subtitle_file, self.font_folder, self.intro_file = None, None, None, None
        self.output_path = None
        self.default_output_name = ""
        self._setup_ui()
        self._connect_signals()
        self.update_ui_state()
        self._load_suffixes()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Zakładka Pliki i Skrypty
        self.main_tab = QWidget()
        self.tabs.addTab(self.main_tab, "Pliki i Skrypty")
        main_tab_layout = QVBoxLayout(self.main_tab)
        input_group = QGroupBox("Pliki wejściowe (przeciągnij i upuść na okno)")
        input_layout = QVBoxLayout(input_group)
        self.mkv_label = QLabel("Plik MKV: Nie wybrano"); self.mkv_button = QPushButton("Wybierz plik MKV")
        self.intro_label = QLabel("Plik wstawki (intro): Nie wybrano"); self.intro_button = QPushButton("Wybierz plik wstawki")
        self.subtitle_label = QLabel("Plik z napisami: Nie wybrano"); self.subtitle_button = QPushButton("Wybierz plik z napisami")
        self.font_label = QLabel("Folder z czcionkami: Nie wybrano"); self.font_button = QPushButton("Wybierz folder z czcionkami")
        input_layout.addWidget(self.mkv_label); input_layout.addWidget(self.mkv_button)
        input_layout.addWidget(self.intro_label); input_layout.addWidget(self.intro_button)
        input_layout.addWidget(self.subtitle_label); input_layout.addWidget(self.subtitle_button)
        input_layout.addWidget(self.font_label); input_layout.addWidget(self.font_button)
        main_tab_layout.addWidget(input_group)
        script_group = QGroupBox("Skrypty")
        script_layout = QVBoxLayout(script_group)
        self.ffmpeg_radio = QRadioButton("Użyj tylko FFmpeg (hardsub)"); self.mkvmerge_ffmpeg_radio = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.mkvmerge_radio = QRadioButton("Użyj tylko mkvmerge (remux)"); self.ffmpeg_intro_radio = QRadioButton("FFmpeg + Wstawka (intro)")
        self.mkvmerge_radio.setChecked(True)
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.ffmpeg_radio, 1); self.button_group.addButton(self.mkvmerge_ffmpeg_radio, 2)
        self.button_group.addButton(self.mkvmerge_radio, 3); self.button_group.addButton(self.ffmpeg_intro_radio, 4)
        script_layout.addWidget(self.ffmpeg_radio); script_layout.addWidget(self.mkvmerge_ffmpeg_radio)
        script_layout.addWidget(self.mkvmerge_radio); script_layout.addWidget(self.ffmpeg_intro_radio)
        main_tab_layout.addWidget(script_group)
        main_tab_layout.addStretch()

        # Zakładka Ustawienia Wyjściowe (ZMIENIONA)
        self.output_tab = QWidget()
        self.tabs.addTab(self.output_tab, "Ustawienia Wyjściowe")
        output_tab_layout = QVBoxLayout(self.output_tab)

        # Wiadomość o niedostępności
        self.output_disabled_label = QLabel("Funkcje tej zakładki nie są dostępne dla tej opcji.")
        self.output_disabled_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_disabled_label.setStyleSheet("font-style: italic; color: #888888;")
        self.output_disabled_label.setVisible(False)
        output_tab_layout.addWidget(self.output_disabled_label)

        self.output_group = QGroupBox("Lokalizacja i nazwa pliku końcowego")
        output_layout = QVBoxLayout(self.output_group)
        self.custom_output_checkbox = QCheckBox("Użyj niestandardowych ustawień wyjściowych")
        output_layout.addWidget(self.custom_output_checkbox)
        location_layout = QHBoxLayout()
        self.output_dir_label = QLabel("Folder wyjściowy:")
        self.output_dir_edit = QLineEdit(); self.output_dir_edit.setPlaceholderText("Domyślnie folder pliku źródłowego")
        self.output_dir_button = QPushButton("Przeglądaj...")
        location_layout.addWidget(self.output_dir_label); location_layout.addWidget(self.output_dir_edit); location_layout.addWidget(self.output_dir_button)
        output_layout.addLayout(location_layout)
        name_layout = QHBoxLayout()
        self.output_name_label = QLabel("Nazwa pliku:")
        self.output_name_edit = QLineEdit(); self.output_name_edit.setPlaceholderText("Domyślnie generowana automatycznie")
        name_layout.addWidget(self.output_name_label); name_layout.addWidget(self.output_name_edit)
        output_layout.addLayout(name_layout)
        output_tab_layout.addWidget(self.output_group)

        self.suffix_group = QGroupBox("Modyfikacja Nazwy Pliku")
        suffix_layout = QVBoxLayout(self.suffix_group)
        top_suffix_layout = QHBoxLayout()
        self.suffix_combo = QComboBox(); self.suffix_combo.setToolTip("Wybierz końcówkę do dodania do nazwy pliku")
        self.apply_suffix_button = QPushButton("Dodaj Końcówkę")
        self.restore_name_button = QPushButton("Przywróć Domyślną")
        top_suffix_layout.addWidget(self.suffix_combo, 2); top_suffix_layout.addWidget(self.apply_suffix_button, 1); top_suffix_layout.addWidget(self.restore_name_button, 1)
        suffix_layout.addLayout(top_suffix_layout)
        bottom_suffix_layout = QHBoxLayout()
        self.custom_suffix_edit = QLineEdit(); self.custom_suffix_edit.setPlaceholderText("Wpisz własną końcówkę (np. _final)")
        self.add_suffix_button = QPushButton("Dodaj")
        self.remove_suffix_button = QPushButton("Usuń")
        bottom_suffix_layout.addWidget(self.custom_suffix_edit, 2); bottom_suffix_layout.addWidget(self.add_suffix_button, 1); bottom_suffix_layout.addWidget(self.remove_suffix_button, 1)
        suffix_layout.addLayout(bottom_suffix_layout)
        output_tab_layout.addWidget(self.suffix_group)
        output_tab_layout.addStretch()

        # Zakładka Opcje Zaawansowane
        self.advanced_tab = QWidget()
        self.tabs.addTab(self.advanced_tab, "Opcje Zaawansowane")
        advanced_tab_layout = QVBoxLayout(self.advanced_tab)
        ffmpeg_group = QGroupBox("Ustawienia enkodera")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        self.ffmpeg_script_label = QLabel("Wybierz skrypt FFmpeg (dla opcji z FFmpeg):")
        self.script1_radio = QRadioButton("CPU (CRF)"); self.script2_radio = QRadioButton("GPU (Nvidia, Bitrate)")
        self.script1_radio.setChecked(True)
        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1); self.script_button_group.addButton(self.script2_radio, 2)
        bitrate_layout = QHBoxLayout()
        self.bitrate_label = QLabel("Bitrate (Mbps):"); self.bitrate_spinbox = QSpinBox()
        self.bitrate_spinbox.setRange(1, 100); self.bitrate_spinbox.setValue(8)
        bitrate_layout.addWidget(self.bitrate_label); bitrate_layout.addWidget(self.bitrate_spinbox)
        ffmpeg_layout.addWidget(self.ffmpeg_script_label); ffmpeg_layout.addWidget(self.script1_radio); ffmpeg_layout.addWidget(self.script2_radio)
        ffmpeg_layout.addLayout(bitrate_layout)
        advanced_tab_layout.addWidget(ffmpeg_group)
        other_group = QGroupBox("Inne")
        other_layout = QVBoxLayout(other_group)
        self.debug_checkbox = QCheckBox("Debug Mode", self)
        self.import_button = QPushButton("Importuj zadania z pliku TXT", self)
        self.help_button = QToolButton(self)
        self.help_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        import_layout = QHBoxLayout(); import_layout.addWidget(self.import_button); import_layout.addWidget(self.help_button)
        other_layout.addWidget(self.debug_checkbox); other_layout.addLayout(import_layout)
        advanced_tab_layout.addWidget(other_group)
        advanced_tab_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        main_layout.addWidget(self.button_box)

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
        self.custom_output_checkbox.toggled.connect(self.update_ui_state)
        self.output_dir_button.clicked.connect(self.select_output_directory)
        self.apply_suffix_button.clicked.connect(self._apply_suffix)
        self.restore_name_button.clicked.connect(self._restore_default_name)
        self.add_suffix_button.clicked.connect(self._add_custom_suffix)
        self.remove_suffix_button.clicked.connect(self._remove_selected_suffix)

    def update_ui_state(self):
        selected_id = self.button_group.checkedId()

        # Logika dla blokowania zakładki "Ustawienia Wyjściowe"
        is_output_tab_disabled = (selected_id == 2)
        self.output_group.setVisible(not is_output_tab_disabled)
        self.suffix_group.setVisible(not is_output_tab_disabled)
        self.output_disabled_label.setVisible(is_output_tab_disabled)

        needs_subtitles = selected_id in [1, 2, 3]
        needs_intro = selected_id == 4
        self.subtitle_label.setEnabled(needs_subtitles); self.subtitle_button.setEnabled(needs_subtitles)
        self.font_label.setEnabled(needs_subtitles); self.font_button.setEnabled(needs_subtitles)
        self.intro_label.setEnabled(needs_intro); self.intro_button.setEnabled(needs_intro)

        use_custom_output = self.custom_output_checkbox.isChecked()
        self.output_dir_label.setEnabled(use_custom_output); self.output_dir_edit.setEnabled(use_custom_output)
        self.output_dir_button.setEnabled(use_custom_output); self.output_name_label.setEnabled(use_custom_output)
        self.output_name_edit.setEnabled(use_custom_output)
        self.suffix_group.setEnabled(use_custom_output)

        ffmpeg_encoder_id = self.script_button_group.checkedId()
        ffmpeg_encoder_options_enabled = selected_id in [1, 2]
        is_gpu_selected = ffmpeg_encoder_options_enabled and ffmpeg_encoder_id == 2
        bitrate_is_relevant = is_gpu_selected or needs_intro
        self.ffmpeg_script_label.setEnabled(ffmpeg_encoder_options_enabled)
        self.script1_radio.setEnabled(ffmpeg_encoder_options_enabled); self.script2_radio.setEnabled(ffmpeg_encoder_options_enabled)
        self.bitrate_label.setEnabled(bitrate_is_relevant); self.bitrate_spinbox.setEnabled(bitrate_is_relevant)

        self.output_name_edit.setText(self._generate_default_output_name())
        self._validate_inputs()

    def _generate_default_output_name(self):
        if not self.mkv_file: return ""
        base_name = self.mkv_file.stem
        script_id = self.button_group.checkedId()

        # Zmieniona logika - tylko zmiana rozszerzenia, bez dodawania końcówek
        extension = ".mp4" if script_id in [1, 4] else ".mkv"

        return f"{base_name}{extension}"

    def update_file_labels(self):
        if self.mkv_file: self.mkv_label.setText(f"Plik MKV: {self.mkv_file.name}")
        if self.intro_file: self.intro_label.setText(f"Plik wstawki: {self.intro_file.name}")
        if self.subtitle_file: self.subtitle_label.setText(f"Plik napisów: {self.subtitle_file.name}")
        if self.font_folder: self.font_label.setText(f"Folder czcionek: {self.font_folder.name}")

        default_name = self._generate_default_output_name()
        self.default_output_name = default_name
        self.output_name_edit.setText(default_name)
        self._load_suffixes()

    def select_output_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder docelowy")
        if path: self.output_dir_edit.setText(path)

    def select_mkv_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik MKV", "", "MKV Files (*.mkv)")
        if path: self.mkv_file = Path(path); self.update_file_labels(); self._validate_inputs()

    def accept(self):
        if not self.batch_tasks and not self._validate_inputs(show_error=True): return

        # Dla zablokowanej opcji (ID 2), niestandardowe wyjście jest niemożliwe
        if self.button_group.checkedId() == 2:
            self.output_path = None
        elif self.custom_output_checkbox.isChecked():
            output_dir, output_name = self.output_dir_edit.text(), self.output_name_edit.text()
            if not output_dir or not output_name:
                QMessageBox.warning(self, "Błąd", "W niestandardowych ustawieniach wyjściowych folder i nazwa pliku nie mogą być puste.")
                return
            if not os.path.isdir(output_dir):
                QMessageBox.warning(self, "Błąd", "Wybrany folder wyjściowy nie istnieje.")
                return
            self.output_path = Path(output_dir) / output_name
        else:
            self.output_path = None

        super().accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()
        else: super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            path = Path(url.toLocalFile())
            if path.suffix.lower() in ['.mp4']: self.intro_file = path
            elif path.suffix.lower() == '.mkv': self.mkv_file = path
            elif path.suffix.lower() == '.ass': self.subtitle_file = path
            elif path.is_dir(): self.font_folder = path
        self.update_file_labels(); self._validate_inputs(); event.acceptProposedAction()

    def _validate_inputs(self, show_error=False):
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        is_valid = False
        selected_id = self.button_group.checkedId()
        if selected_id in [1, 2, 3]: is_valid = all([self.mkv_file, self.subtitle_file, self.font_folder])
        elif selected_id == 4: is_valid = all([self.mkv_file, self.intro_file])
        if ok_button: ok_button.setEnabled(is_valid)
        if not is_valid and show_error: QMessageBox.warning(self, "Błąd", "Uzupełnij wszystkie wymagane pola dla wybranego skryptu.");
        return is_valid

    def select_intro_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz wstawkę", "", "Video Files (*.mp4 *.mkv)")
        if path: self.intro_file = Path(path); self.update_file_labels(); self._validate_inputs()

    def select_subtitle_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz napisy", "", "ASS Files (*.ass)")
        if path: self.subtitle_file = Path(path); self.update_file_labels(); self._validate_inputs()

    def select_font_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami")
        if path: self.font_folder = Path(path); self.update_file_labels(); self._validate_inputs()

    def _load_suffixes(self):
        self.suffix_combo.clear()
        custom_suffixes = self.settings.value("custom_suffixes", [], type=str)
        self.suffix_combo.addItems(custom_suffixes)

    def _save_suffixes(self):
        custom_suffixes = []
        for i in range(self.suffix_combo.count()):
            text = self.suffix_combo.itemText(i)
            if text:
                custom_suffixes.append(text)

        unique_custom = sorted(list(set(custom_suffixes)))
        self.settings.setValue("custom_suffixes", unique_custom)

    def _apply_suffix(self):
        suffix = self.suffix_combo.currentText()
        if not suffix: return
        current_name = self.output_name_edit.text()
        p = Path(current_name)
        new_name = f"{p.stem}{suffix}{p.suffix}"
        self.output_name_edit.setText(new_name)

    def _restore_default_name(self):
        self.output_name_edit.setText(self.default_output_name)

    def _add_custom_suffix(self):
        new_suffix = self.custom_suffix_edit.text().strip()
        if not new_suffix:
            QMessageBox.warning(self, "Uwaga", "Pole z końcówką nie może być puste.")
            return

        items = [self.suffix_combo.itemText(i) for i in range(self.suffix_combo.count())]
        if new_suffix in items:
            QMessageBox.information(self, "Informacja", "Taka końcówka już istnieje na liście.")
            return

        self.suffix_combo.addItem(new_suffix)
        self.custom_suffix_edit.clear()
        self._save_suffixes()
        QMessageBox.information(self, "Sukces", f"Dodano nową końcówkę: {new_suffix}")

    def _remove_selected_suffix(self):
        current_index = self.suffix_combo.currentIndex()
        current_text = self.suffix_combo.currentText()
        if not current_text or current_index == -1: return

        reply = QMessageBox.question(self, "Potwierdzenie", f"Czy na pewno chcesz usunąć końcówkę '{current_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.suffix_combo.removeItem(current_index)
            self._save_suffixes()
            QMessageBox.information(self, "Sukces", "Usunięto wybraną końcówkę.")

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
            while len(parts) < 8:
                parts.append("")
            if len(parts) > 8:
                fatal_errors.append(f"Linia {line_num}: Zbyt wiele pól (oczekiwano 8, otrzymano {len(parts)}).")
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
            elif script_type not in [0, 3]:
                 line_errors.append(f"Nieznany typ skryptu: {script_type}.")
            if not mkv_path_str and script_type != 0:
                line_errors.append("Brak ścieżki do pliku MKV.")
            if line_errors:
                fatal_errors.append(f"Linia {line_num}: " + ", ".join(line_errors))
                continue
            mkv_path = Path(mkv_path_str) if mkv_path_str else None
            subtitle_path = Path(sub_path_str) if sub_path_str else None
            font_folder = Path(font_path_str) if font_path_str else None
            intro_path = Path(intro_path_str) if intro_path_str else None
            line_warnings = []
            if mkv_path and not mkv_path.is_file(): line_warnings.append(f"Plik MKV nie istnieje: '{mkv_path_str}'")
            if script_type in [1, 2, 3]:
                if subtitle_path and not subtitle_path.is_file(): line_warnings.append(f"Plik napisów nie istnieje: '{sub_path_str}'")
                if font_folder and not font_folder.is_dir(): line_warnings.append(f"Folder czcionek nie istnieje: '{font_path_str}'")
            if script_type == 4:
                if intro_path and not intro_path.is_file(): line_warnings.append(f"Plik wstawki nie istnieje: '{intro_path_str}'")

            task_data = (mkv_path, subtitle_path, font_folder, script_type, ffmpeg_type, bitrate, debug, intro_path, None)
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
