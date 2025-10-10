# component_selection_dialog.py (Wersja finalna: stary, stabilny kod + moduł importu)

import os
import platform
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog,
                             QRadioButton, QButtonGroup, QSpinBox, QCheckBox,
                             QDialogButtonBox, QMessageBox, QHBoxLayout, QLineEdit,
                             QToolButton, QStyle, QTabWidget, QWidget, QGroupBox,
                             QComboBox)
from PyQt6.QtCore import Qt, QSettings
from mkv_info_dialog import MkvInfoDialog
from batch_import_logic import BatchImportLogic

class ComponentSelectionDialog(QDialog):
    def __init__(self, use_per_option_paths=False, parent=None, is_flatpak=False):
        super().__init__(parent)
        self.use_per_option_paths = use_per_option_paths
        self.is_flatpak = is_flatpak
        self.is_windows = platform.system() == "Windows"
        self.setWindowTitle("Wybierz Komponenty")
        self.setGeometry(100, 100, 650, 650)
        self.setAcceptDrops(True)
        self.settings = QSettings("settings.ini", QSettings.Format.IniFormat)
        self.batch_tasks = []
        self.mkv_file, self.subtitle_file, self.font_folder, self.intro_file = None, None, None, None
        self.output_path = None
        self.default_output_name = ""

        # --- ZMIANA 2: Inicjalizacja pomocnika ---
        self.batch_import_handler = BatchImportLogic(self)

        self._setup_ui()
        self._connect_signals()
        self.update_ui_state()
        self._load_suffixes()
        self._apply_initial_paths()

    def _apply_initial_paths(self):

        default_name = self.settings.value("remux/subtitle_track_name", "")
        self.subtitle_track_name_edit.setText(default_name)

        intro_path_str = self.settings.value("file_intro", "")
        if intro_path_str and Path(intro_path_str).is_file():
            self.intro_file = Path(intro_path_str)
            self.update_file_labels()

        if self.use_per_option_paths:
            current_id = str(self.button_group.checkedId())
            saved_path = self.settings.value(f"path_{current_id}", "")
            if saved_path:
                self.output_dir_edit.setText(saved_path)
                self.custom_output_checkbox.setChecked(True)

    def _on_script_option_changed(self):
        if self.use_per_option_paths:
            current_id = str(self.button_group.checkedId())
            if current_id == '2':
                self.output_dir_edit.clear()
                self.custom_output_checkbox.setChecked(False)
                return

            saved_path = self.settings.value(f"path_{current_id}", "")
            self.output_dir_edit.setText(saved_path)
            self.custom_output_checkbox.setChecked(bool(saved_path))

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        self.main_tab = QWidget()
        self.tabs.addTab(self.main_tab, "Pliki i Skrypty")
        main_tab_layout = QVBoxLayout(self.main_tab)
        input_group = QGroupBox("Pliki wejściowe (przeciągnij i upuść na okno)")
        input_layout = QVBoxLayout(input_group)
        self.mkv_label = QLabel("Plik MKV: Nie wybrano")
        self.mkv_button = QPushButton("Wybierz plik MKV")
        self.intro_label = QLabel("Plik wstawki (intro): Nie wybrano")
        self.intro_button = QPushButton("Wybierz plik wstawki")
        self.subtitle_label = QLabel("Plik z napisami: Nie wybrano")
        self.subtitle_button = QPushButton("Wybierz plik z napisami")
        self.font_label = QLabel("Folder z czcionkami: Nie wybrano")
        self.font_button = QPushButton("Wybierz folder z czcionkami")
        input_layout.addWidget(self.mkv_label)
        input_layout.addWidget(self.mkv_button)
        input_layout.addWidget(self.intro_label)
        input_layout.addWidget(self.intro_button)
        input_layout.addWidget(self.subtitle_label)
        input_layout.addWidget(self.subtitle_button)
        input_layout.addWidget(self.font_label)
        input_layout.addWidget(self.font_button)
        main_tab_layout.addWidget(input_group)
        script_group = QGroupBox("Skrypty")
        script_layout = QVBoxLayout(script_group)
        self.ffmpeg_radio = QRadioButton("Użyj tylko FFmpeg (hardsub)")
        self.mkvmerge_ffmpeg_radio = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.mkvmerge_radio = QRadioButton("Użyj tylko mkvmerge (remux)")
        self.ffmpeg_intro_radio = QRadioButton("FFmpeg + Wstawka (intro)")
        self.mkvmerge_radio.setChecked(True)
        self.button_group = QButtonGroup()
        self.button_group.addButton(self.ffmpeg_radio, 1)
        self.button_group.addButton(self.mkvmerge_ffmpeg_radio, 2)
        self.button_group.addButton(self.mkvmerge_radio, 3)
        self.button_group.addButton(self.ffmpeg_intro_radio, 4)
        script_layout.addWidget(self.ffmpeg_radio)
        script_layout.addWidget(self.mkvmerge_ffmpeg_radio)
        script_layout.addWidget(self.mkvmerge_radio)
        script_layout.addWidget(self.ffmpeg_intro_radio)
        main_tab_layout.addWidget(script_group)
        file_options_group = QGroupBox("Opcje Pliku")
        file_options_layout = QHBoxLayout(file_options_group)
        self.info_button = QPushButton("Pokaż informacje o pliku MKV")
        self.info_button.setToolTip("Otwiera nowe okno ze szczegółami pliku wideo")
        self.info_button.setEnabled(False)
        file_options_layout.addWidget(self.info_button)
        main_tab_layout.addWidget(file_options_group)
        main_tab_layout.addStretch()
        self.output_tab = QWidget()
        self.tabs.addTab(self.output_tab, "Ustawienia Wyjściowe")
        output_tab_layout = QVBoxLayout(self.output_tab)
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
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Domyślnie folder pliku źródłowego")
        self.output_dir_button = QPushButton("Przeglądaj...")
        location_layout.addWidget(self.output_dir_label)
        location_layout.addWidget(self.output_dir_edit)
        location_layout.addWidget(self.output_dir_button)
        output_layout.addLayout(location_layout)
        name_layout = QHBoxLayout()
        self.output_name_label = QLabel("Nazwa pliku:")
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText("Domyślnie generowana automatycznie")
        name_layout.addWidget(self.output_name_label)
        name_layout.addWidget(self.output_name_edit)
        output_layout.addLayout(name_layout)
        output_tab_layout.addWidget(self.output_group)
        self.suffix_group = QGroupBox("Modyfikacja Nazwy Pliku")
        suffix_layout = QVBoxLayout(self.suffix_group)
        top_suffix_layout = QHBoxLayout()
        self.suffix_combo = QComboBox()
        self.suffix_combo.setToolTip("Wybierz końcówkę do dodania do nazwy pliku")
        self.apply_suffix_button = QPushButton("Dodaj Końcówkę")
        self.restore_name_button = QPushButton("Przywróć Domyślną")
        top_suffix_layout.addWidget(self.suffix_combo, 2)
        top_suffix_layout.addWidget(self.apply_suffix_button, 1)
        top_suffix_layout.addWidget(self.restore_name_button, 1)
        suffix_layout.addLayout(top_suffix_layout)
        bottom_suffix_layout = QHBoxLayout()
        self.custom_suffix_edit = QLineEdit()
        self.custom_suffix_edit.setPlaceholderText("Wpisz własną końcówkę (np. _final)")
        self.add_suffix_button = QPushButton("Dodaj")
        self.remove_suffix_button = QPushButton("Usuń")
        bottom_suffix_layout.addWidget(self.custom_suffix_edit, 2)
        bottom_suffix_layout.addWidget(self.add_suffix_button, 1)
        bottom_suffix_layout.addWidget(self.remove_suffix_button, 1)
        suffix_layout.addLayout(bottom_suffix_layout)
        output_tab_layout.addWidget(self.suffix_group)
        output_tab_layout.addStretch()
        self.advanced_tab = QWidget()
        self.tabs.addTab(self.advanced_tab, "Opcje Zaawansowane")
        advanced_tab_layout = QVBoxLayout(self.advanced_tab)
        ffmpeg_group = QGroupBox("Ustawienia enkodera")
        ffmpeg_layout = QVBoxLayout(ffmpeg_group)
        self.ffmpeg_script_label = QLabel("Wybierz skrypt FFmpeg (dla opcji z FFmpeg):")
        self.script1_radio = QRadioButton("CPU (CRF)")
        self.script2_radio = QRadioButton("GPU (Nvidia CUDA)")
        self.script3_radio = QRadioButton("GPU (Intel/AMD VA-API)")
        self.script1_radio.setChecked(True)
        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1)
        self.script_button_group.addButton(self.script2_radio, 2)
        self.script_button_group.addButton(self.script3_radio, 3)

        bitrate_layout = QHBoxLayout()
        self.bitrate_label = QLabel("Bitrate (Mbps):")
        self.bitrate_spinbox = QSpinBox()
        self.bitrate_spinbox.setRange(1, 100)
        default_bitrate = self.settings.value("processing/default_gpu_bitrate", 8, type=int)
        self.bitrate_spinbox.setValue(default_bitrate)
        bitrate_layout.addWidget(self.bitrate_label)
        bitrate_layout.addWidget(self.bitrate_spinbox)
        ffmpeg_layout.addWidget(self.ffmpeg_script_label)
        ffmpeg_layout.addWidget(self.script1_radio)
        ffmpeg_layout.addWidget(self.script2_radio)
        ffmpeg_layout.addWidget(self.script3_radio)
        ffmpeg_layout.addLayout(bitrate_layout)

        self.encoder_warning_label = QLabel("")
        self.encoder_warning_label.setStyleSheet("color: #E67E22; font-style: italic;")
        ffmpeg_layout.addWidget(self.encoder_warning_label)
        advanced_tab_layout.addWidget(ffmpeg_group)

                # --- NOWA SEKCJA DLA OPCJI REMUX ---
        remux_group = QGroupBox("Ustawienia remuxa (mkvmerge)")
        remux_group.setObjectName("remux_group")
        remux_layout = QVBoxLayout(remux_group)

        subtitle_track_layout = QHBoxLayout()
        self.subtitle_track_label = QLabel("Nazwa ścieżki napisów:")
        self.subtitle_track_name_edit = QLineEdit()
        self.subtitle_track_name_edit.setPlaceholderText("Domyślnie z ustawień globalnych")

        subtitle_track_layout.addWidget(self.subtitle_track_label)
        subtitle_track_layout.addWidget(self.subtitle_track_name_edit)

        remux_layout.addLayout(subtitle_track_layout)

        movie_name_layout = QHBoxLayout()
        self.movie_name_checkbox = QCheckBox("Zachowaj Movie Name")
        self.movie_name_edit = QLineEdit()
        self.movie_name_edit.setPlaceholderText("Wpisz nową nazwę filmu")
        movie_name_layout.addWidget(self.movie_name_checkbox)
        movie_name_layout.addWidget(self.movie_name_edit)
        remux_layout.addLayout(movie_name_layout)

        advanced_tab_layout.addWidget(remux_group)



        other_group = QGroupBox("Inne")
        other_layout = QVBoxLayout(other_group)
        self.debug_checkbox = QCheckBox("Debug Mode", self)
        self.import_button = QPushButton("Importuj zadania z pliku TXT", self)
        self.help_button = QToolButton(self)
        self.help_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        import_layout = QHBoxLayout()
        import_layout.addWidget(self.import_button)
        import_layout.addWidget(self.help_button)
        other_layout.addWidget(self.debug_checkbox)
        other_layout.addLayout(import_layout)
        advanced_tab_layout.addWidget(other_group)
        advanced_tab_layout.addStretch()
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        main_layout.addWidget(self.button_box)

    def _connect_signals(self):
        self.info_button.clicked.connect(self.show_mkv_info_dialog)
        self.mkv_button.clicked.connect(self.select_mkv_file)
        self.intro_button.clicked.connect(self.select_intro_file)
        self.subtitle_button.clicked.connect(self.select_subtitle_file)
        self.font_button.clicked.connect(self.select_font_folder)
        self.button_group.buttonClicked.connect(self.update_ui_state)
        self.button_group.buttonClicked.connect(self._on_script_option_changed)
        self.script_button_group.buttonClicked.connect(self.update_ui_state)

        # --- ZMIANA 3: Podłączenie do nowego modułu ---
        self.import_button.clicked.connect(self.batch_import_handler.import_from_txt)
        self.help_button.clicked.connect(self.batch_import_handler.show_import_help_dialog)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.custom_output_checkbox.toggled.connect(self.update_ui_state)
        self.output_dir_button.clicked.connect(self.select_output_directory)
        self.apply_suffix_button.clicked.connect(self._apply_suffix)
        self.restore_name_button.clicked.connect(self._restore_default_name)
        self.add_suffix_button.clicked.connect(self._add_custom_suffix)
        self.remove_suffix_button.clicked.connect(self._remove_selected_suffix)
        self.movie_name_checkbox.toggled.connect(self.update_ui_state)

    def show_mkv_info_dialog(self):
        if self.mkv_file:
            dialog = MkvInfoDialog(self.mkv_file, self)
            dialog.exec()

    def update_ui_state(self):
        self.info_button.setEnabled(self.mkv_file is not None and self.mkv_file.is_file())
        selected_id = self.button_group.checkedId()
        is_output_tab_disabled = (selected_id == 2)
        self.output_group.setVisible(not is_output_tab_disabled)
        self.suffix_group.setVisible(not is_output_tab_disabled)
        self.output_disabled_label.setVisible(is_output_tab_disabled)
        needs_subtitles = selected_id in [1, 2, 3]
        needs_intro = selected_id == 4
        self.subtitle_label.setEnabled(needs_subtitles)
        self.subtitle_button.setEnabled(needs_subtitles)
        self.font_label.setEnabled(needs_subtitles)
        self.font_button.setEnabled(needs_subtitles)
        self.intro_label.setEnabled(needs_intro)
        self.intro_button.setEnabled(needs_intro)
        use_custom_output = self.custom_output_checkbox.isChecked()
        self.output_dir_label.setEnabled(use_custom_output)
        self.output_dir_edit.setEnabled(use_custom_output)
        self.output_dir_button.setEnabled(use_custom_output)
        self.output_name_label.setEnabled(use_custom_output)
        self.output_name_edit.setEnabled(use_custom_output)
        self.suffix_group.setEnabled(use_custom_output)
        ffmpeg_encoder_id = self.script_button_group.checkedId()
        ffmpeg_encoder_options_enabled = selected_id in [1, 2, 4]
        is_gpu_selected = ffmpeg_encoder_options_enabled and ffmpeg_encoder_id in [2, 3]
        bitrate_is_relevant = is_gpu_selected or needs_intro
        self.ffmpeg_script_label.setEnabled(ffmpeg_encoder_options_enabled)
        self.bitrate_label.setEnabled(bitrate_is_relevant)
        self.bitrate_spinbox.setEnabled(bitrate_is_relevant)

        # Scentralizowana logika widoczności i stanu przycisków enkodera
        self.script1_radio.setEnabled(ffmpeg_encoder_options_enabled)
        self.script2_radio.setVisible(not self.is_flatpak)
        self.script2_radio.setEnabled(ffmpeg_encoder_options_enabled and not self.is_flatpak)
        self.script3_radio.setVisible(not self.is_flatpak and not self.is_windows)
        self.script3_radio.setEnabled(ffmpeg_encoder_options_enabled and not self.is_flatpak and not self.is_windows)
        self.movie_name_edit.setDisabled(self.movie_name_checkbox.isChecked())
                # --- DODANA LOGIKA DLA NOWEGO POLA ---
        # Znajdź grupę remux (jeśli istnieje) i ustaw jej widoczność
        remux_group = self.findChild(QGroupBox, "remux_group") # Musisz nadać jej nazwę w _setup_ui
        if remux_group: # Bezpieczne sprawdzenie
            is_remux_relevant = selected_id in [2, 3] # Aktywne dla skryptów mkvmerge
            remux_group.setEnabled(is_remux_relevant)
        # ------------------------------------------
        # Tylko aktualizuj domyślną nazwę, jeśli użytkownik NIE jest w trybie niestandardowym
        if not self.custom_output_checkbox.isChecked():
            self.output_name_edit.setText(self._generate_default_output_name())

        # Logika ostrzeżeń o opcjach eksperymentalnych
        warning_text = ""
        if selected_id == 4 and ffmpeg_encoder_id in [2, 3]:
            warning_text = "Opcja GPU dla skryptu z wstawką jest EKSPERYMENTALNA."
        elif selected_id in [1, 2] and ffmpeg_encoder_id == 3:
            warning_text = "Opcja VA-API dla tego skryptu jest EKSPERYMENTALNA."
        
        self.encoder_warning_label.setText(warning_text)
        self.encoder_warning_label.setVisible(bool(warning_text))

        self._validate_inputs()

    def _generate_default_output_name(self):
        if not self.mkv_file:
            return ""
        base_name = self.mkv_file.stem
        script_id = self.button_group.checkedId()
        extension = ".mp4" if script_id in [1, 4] else ".mkv"
        return f"{base_name}{extension}"

    def update_file_labels(self):
        if self.mkv_file:
            self.mkv_label.setText(f"Plik MKV: {self.mkv_file.name}")
        if self.intro_file:
            self.intro_label.setText(f"Plik wstawki: {self.intro_file.name}")
        if self.subtitle_file:
            self.subtitle_label.setText(f"Plik napisów: {self.subtitle_file.name}")
        if self.font_folder:
            self.font_label.setText(f"Folder czcionek: {self.font_folder.name}")
        default_name = self._generate_default_output_name()
        self.default_output_name = default_name
        self.output_name_edit.setText(default_name)
        self._load_suffixes()

    def select_output_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder docelowy")
        if path:
            self.output_dir_edit.setText(path)

    def accept(self):
        # Jeśli zadania pochodzą z importu pliku, natychmiast zamknij okno.
        if self.batch_tasks:
            super().accept()
            return

        # Dla pojedynczego zadania, najpierw zweryfikuj wymagane pliki wejściowe.
        if not self._validate_inputs(show_error=True):
            return

        # Sprawdź, czy użytkownik chce użyć niestandardowych ustawień.
        if self.custom_output_checkbox.isChecked():
            # Jeśli tak, zweryfikuj podane przez niego ścieżki.
            output_dir = self.output_dir_edit.text()
            output_name = self.output_name_edit.text()
            if not output_dir or not output_name:
                QMessageBox.warning(self, "Błąd", "W niestandardowych ustawieniach folder i nazwa pliku nie mogą być puste.")
                return
            if not os.path.isdir(output_dir):
                QMessageBox.warning(self, "Błąd", "Wybrany folder wyjściowy nie istnieje.")
                return
            # Ustaw pełną, niestandardową ścieżkę wyjściową.
            self.output_path = Path(output_dir) / output_name
        else:
            # Jeśli checkbox jest ODZNACZONY, jawnie ustawiamy ścieżkę na None.
            # To jest sygnał dla ProcessManagera, aby sam wygenerował domyślną ścieżkę.
            self.output_path = None

        # Skrypt typu 2 nigdy nie używa ścieżki wyjściowej, więc dla pewności ją zerujemy.
        if self.button_group.checkedId() == 2:
            self.output_path = None

        super().accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            path = Path(url.toLocalFile())
            if path.suffix.lower() in ['.mp4']:
                self.intro_file = path
            elif path.suffix.lower() == '.mkv':
                self.mkv_file = path
            elif path.suffix.lower() == '.ass':
                self.subtitle_file = path
            elif path.is_dir():
                self.font_folder = path
        self.update_file_labels()
        self._validate_inputs()
        event.acceptProposedAction()
        self.update_ui_state()

    def _validate_inputs(self, show_error=False):
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        is_valid = False
        selected_id = self.button_group.checkedId()
        if selected_id in [1, 2, 3]:
            is_valid = all([self.mkv_file, self.subtitle_file, self.font_folder])
        elif selected_id == 4:
            is_valid = all([self.mkv_file, self.intro_file])
        if ok_button:
            ok_button.setEnabled(is_valid)
        if not is_valid and show_error:
            QMessageBox.warning(self, "Błąd", "Uzupełnij wszystkie wymagane pola dla wybranego skryptu.")
        return is_valid

    def _get_last_used_directory(self):
        return self.settings.value("last_used_directory", str(Path.home()))

    def _set_last_used_directory(self, path):
        self.settings.setValue("last_used_directory", str(Path(path).parent))

    def _set_last_used_folder(self, path):
        self.settings.setValue("last_used_directory", str(path))

    def select_mkv_file(self):
        last_dir = self._get_last_used_directory()
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik MKV", last_dir, "MKV Files (*.mkv)")
        if path:
            self.mkv_file = Path(path)
            self._set_last_used_directory(path)
            self.update_file_labels()
            self._validate_inputs()
            self.update_ui_state()

    def select_intro_file(self):
        last_dir = self._get_last_used_directory()
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz wstawkę", last_dir, "Video Files (*.mp4 *.mkv)")
        if path:
            self.intro_file = Path(path)
            self._set_last_used_directory(path)
            self.update_file_labels()
            self._validate_inputs()
            self.update_ui_state()

    def select_subtitle_file(self):
        last_dir = self._get_last_used_directory()
        path, _ = QFileDialog.getOpenFileName(self, "Wybierz napisy", last_dir, "ASS Files (*.ass)")
        if path:
            self.subtitle_file = Path(path)
            self._set_last_used_directory(path)
            self.update_file_labels()
            self._validate_inputs()
            self.update_ui_state()

    def select_font_folder(self):
        last_dir = self._get_last_used_directory()
        path = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami", last_dir)
        if path:
            self.font_folder = Path(path)
            self._set_last_used_folder(path)
            self.update_file_labels()
            self._validate_inputs()
            self.update_ui_state()

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
        if not suffix:
            return
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
        if not current_text or current_index == -1:
            return
        reply = QMessageBox.question(self, "Potwierdzenie", f"Czy na pewno chcesz usunąć końcówkę '{current_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.suffix_combo.removeItem(current_index)
            self._save_suffixes()
            QMessageBox.information(self, "Sukces", "Usunięto wybraną końcówkę.")

    @property
    def selected_script(self): return self.button_group.checkedId()
    @property
    def selected_ffmpeg_script(self): return self.script_button_group.checkedId()
    @property
    def gpu_bitrate(self): return self.bitrate_spinbox.value()
    @property
    def debug_mode(self): return self.debug_checkbox.isChecked()
    @property
    def subtitle_track_name(self):
        # Sprawdź, czy pole edycji istnieje
        if hasattr(self, 'subtitle_track_name_edit'):
            # Pobierz tekst z pola. Jeśli jest pusty, zwróć pusty string.
            return self.subtitle_track_name_edit.text()
        # Jeśli pole z jakiegoś powodu nie istnieje, zwróć pusty string.
        return ""

    @property
    def movie_name(self):
        if self.movie_name_checkbox.isChecked():
            return " "  # Preserve original by returning a space
        return self.movie_name_edit.text()

