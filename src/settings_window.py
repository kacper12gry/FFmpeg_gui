import platform
import shutil
import subprocess
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox, 
                             QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
                             QCheckBox, QDialogButtonBox, QFileDialog, QComboBox, QHBoxLayout,
                             QMessageBox, QSplitter, QListWidget, QTextEdit, QListWidgetItem,
                             QRadioButton, QButtonGroup, QInputDialog)
from PyQt6.QtGui import QIcon, QPixmap
import urllib.request
from PyQt6.QtCore import QSettings, Qt, QProcess, QEvent, QThread, pyqtSignal

# --- Nowa klasa do pobierania obrazka w tle ---
class ImageDownloader(QThread):
    image_ready = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            req = urllib.request.Request(self.url, headers=headers)
            with urllib.request.urlopen(req) as response:
                image_data = response.read()
                self.image_ready.emit(image_data)
        except Exception as e:
            self.error_occurred.emit(str(e))

# --- Nowe okno do wyświetlania Easter Egga ---
class EasterEggDialog(QDialog):
    def __init__(self, image_data, signature_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Niespodzianka!")
        
        layout = QVBoxLayout(self)
        
        # Obrazek
        image_label = QLabel()
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        image_label.setPixmap(pixmap.scaled(512, 512, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

        # Podpis
        signature_label = QLabel(signature_text)
        signature_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signature_label.setStyleSheet("font-style: italic; margin-top: 10px;")
        layout.addWidget(signature_label)

        # Przycisk zamknięcia
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.button(QDialogButtonBox.StandardButton.Close).setText("Zamknij")
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

class SettingsWindow(QDialog):
    def __init__(self, settings: QSettings, plugin_manager, output_window, parent=None, version="N/A", is_flatpak=False):
        super().__init__(parent)
        self.settings = settings
        self.plugin_manager = plugin_manager
        self.output_window = output_window
        self.process = None
        self.is_windows = platform.system() == "Windows"
        self.app_version = version
        self.is_flatpak = is_flatpak
        self.click_counter = 0
        self.image_worker = None # Do przechowywania referencji do wątku
        self.setWindowTitle("Ustawienia Programu")
        self.setMinimumWidth(650)

        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Inicjalizacja zakładek
        self.general_tab = QWidget()
        self.paths_tab = QWidget()
        self.presets_tab = QWidget() # NOWA ZAKŁADKA
        self.processing_tab = QWidget()
        self.diagnostics_tab = QWidget()
        self.about_tab = QWidget()

        self.tabs.addTab(self.general_tab, "Ogólne")
        self.tabs.addTab(self.paths_tab, "Ścieżki")
        self.tabs.addTab(self.presets_tab, "Presety") # NOWA ZAKŁADKA
        self.tabs.addTab(self.processing_tab, "Przetwarzanie")
        self.tabs.addTab(self.diagnostics_tab, "Diagnostyka")
        self.tabs.addTab(self.about_tab, "O Programie")

        self._create_general_tab()
        self._create_paths_tab()
        self._create_presets_tab() # NOWA METODA
        self._create_processing_tab()
        self._create_diagnostics_tab()
        self._create_about_tab()

        # Przyciski OK, Anuluj
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("OK")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.load_settings()
        self._load_presets_list() # Wczytaj presety do nowej zakładki
        self._get_gpu_info()

    def _get_gpu_info(self):
        try:
            if self.is_windows:
                command = "wmic path win32_videocontroller get name"
                result = subprocess.run(command, capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                gpu_info = result.stdout.strip().split('\n')[1]
            else:
                command = "lspci | grep VGA"
                result = subprocess.run(command, capture_output=True, text=True, check=True, shell=True)
                gpu_info = result.stdout.strip().split(': ', 2)[-1]
            self.gpu_info_label.setText(gpu_info)
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
            self.gpu_info_label.setText("Nie udało się pobrać informacji o karcie graficznej.")

    def _create_general_tab(self):
        layout = QFormLayout(self.general_tab)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.theme_combo = QComboBox()
        self.themes = {
            "system": "Systemowy", 
            "dark": "Ciemny", 
            "pro_light": "Jasny",
            "light": "Fusion"
        }
        self.theme_combo.addItems(self.themes.values())
        layout.addRow("Motyw aplikacji:", self.theme_combo)

        self.style_engine_label = QLabel("Silnik motywu systemowego:")
        self.style_engine_combo = QComboBox()
        self.style_engines = {
            "default": "Domyślny",
            "breeze": "Breeze",
            "kvantum": "Kvantum",
            "fusion": "Fusion"
        }
        self.style_engine_combo.addItems(self.style_engines.values())
        layout.addRow(self.style_engine_label, self.style_engine_combo)

        self.discord_rpc_checkbox = QCheckBox("Włącz integrację z Discord (RPC)")
        self.discord_rpc_checkbox.setVisible(not self.is_flatpak)
        layout.addRow(self.discord_rpc_checkbox)

        self.detailed_view_checkbox = QCheckBox("Używaj szczegółowego widoku listy zadań")
        layout.addRow(self.detailed_view_checkbox)

        self.show_summary_checkbox = QCheckBox("Pokazuj podsumowanie przed dodaniem zadania")
        layout.addRow(self.show_summary_checkbox)

        self.theme_combo.currentTextChanged.connect(self._update_style_engine_visibility)
        self._update_style_engine_visibility(self.theme_combo.currentText())

    def _update_style_engine_visibility(self, theme_text):
        is_system_theme = (theme_text == self.themes["system"])
        should_be_visible = is_system_theme and not self.is_windows
        self.style_engine_label.setVisible(should_be_visible)
        self.style_engine_combo.setVisible(should_be_visible)

    def _create_paths_tab(self):
        layout = QVBoxLayout(self.paths_tab)
        group_box = QGroupBox("Domyślne ścieżki")
        form_layout = QFormLayout(group_box)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.path_edits = {}
        path_labels = {
            "path_1": "Folder dla 'Tylko FFmpeg':",
            "path_3": "Folder dla 'Tylko mkvmerge':",
            "path_4": "Folder dla 'FFmpeg + Wstawka':",
            "file_intro": "Plik wstawki (intro):"
        }

        for key, text in path_labels.items():
            self.path_edits[key] = self._create_path_row(form_layout, text, is_file=key.startswith("file_"))

        layout.addWidget(group_box)

    def _create_presets_tab(self):
        # --- Główny layout zakładki ---
        tab_layout = QHBoxLayout(self.presets_tab)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        tab_layout.addWidget(splitter)

        # --- Lewy panel: Lista presetów i przyciski ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.presets_list_widget = QListWidget()
        self.presets_list_widget.currentItemChanged.connect(self._display_preset_details)
        left_layout.addWidget(self.presets_list_widget)

        preset_buttons_layout = QHBoxLayout()
        new_preset_button = QPushButton("Nowy")
        delete_preset_button = QPushButton("Usuń")
        new_preset_button.clicked.connect(self._new_preset)
        delete_preset_button.clicked.connect(self._delete_preset)
        preset_buttons_layout.addWidget(new_preset_button)
        preset_buttons_layout.addWidget(delete_preset_button)
        left_layout.addLayout(preset_buttons_layout)

        # --- Prawy panel: Formularz edycji presetu ---
        self.right_panel = QWidget()
        right_layout = QFormLayout(self.right_panel)
        right_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.right_panel.setEnabled(False) # Domyślnie wyłączony

        # Kontrolki formularza (muszą być atrybutami klasy, by mieć do nich dostęp)
        # 1. Główny skrypt
        self.preset_script_group = QButtonGroup(self)
        self.preset_script1 = QRadioButton("Tylko FFmpeg (hardsub)")
        self.preset_script2 = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.preset_script3 = QRadioButton("Użyj tylko mkvmerge (remux)")
        self.preset_script4 = QRadioButton("FFmpeg + Wstawka (intro)")
        self.preset_script_group.addButton(self.preset_script1, 1)
        self.preset_script_group.addButton(self.preset_script2, 2)
        self.preset_script_group.addButton(self.preset_script3, 3)
        self.preset_script_group.addButton(self.preset_script4, 4)
        script_box = QVBoxLayout()
        script_box.addWidget(self.preset_script1)
        script_box.addWidget(self.preset_script2)
        script_box.addWidget(self.preset_script3)
        script_box.addWidget(self.preset_script4)
        right_layout.addRow("Główny skrypt:", script_box)

        # 2. Skrypt enkodera FFmpeg
        self.preset_ffmpeg_group = QButtonGroup(self)
        self.preset_ffmpeg1 = QRadioButton("CPU (CRF)")
        self.preset_ffmpeg2 = QRadioButton("GPU (Nvidia CUDA)")
        self.preset_ffmpeg3 = QRadioButton("GPU (Intel/AMD VA-API)")
        self.preset_ffmpeg_group.addButton(self.preset_ffmpeg1, 1)
        self.preset_ffmpeg_group.addButton(self.preset_ffmpeg2, 2)
        self.preset_ffmpeg_group.addButton(self.preset_ffmpeg3, 3)
        ffmpeg_box = QVBoxLayout()
        ffmpeg_box.addWidget(self.preset_ffmpeg1)
        ffmpeg_box.addWidget(self.preset_ffmpeg2)
        ffmpeg_box.addWidget(self.preset_ffmpeg3)
        right_layout.addRow("Enkoder FFmpeg:", ffmpeg_box)

        # 3. Bitrate
        self.preset_bitrate_spin = QSpinBox()
        self.preset_bitrate_spin.setRange(1, 100)
        self.preset_bitrate_spin.setSuffix(" Mbps")
        right_layout.addRow("Bitrate (GPU/Wstawka):", self.preset_bitrate_spin)

        # 4. Nazwa ścieżki napisów
        self.preset_subtitle_name_edit = QLineEdit()
        right_layout.addRow("Nazwa ścieżki napisów:", self.preset_subtitle_name_edit)

        # 5. Nazwa filmu (mkvmerge)
        self.preset_movie_name_edit = QLineEdit()
        self.preset_keep_movie_name_check = QCheckBox("Zachowaj oryginalną")
        movie_name_layout = QHBoxLayout()
        movie_name_layout.addWidget(self.preset_movie_name_edit)
        movie_name_layout.addWidget(self.preset_keep_movie_name_check)
        right_layout.addRow("Tytuł filmu (mkvmerge):", movie_name_layout)

        # 6. Inne opcje
        self.preset_debug_check = QCheckBox("Debug Mode")
        self.preset_custom_output_check = QCheckBox("Niestandardowe wyjście")
        other_box = QVBoxLayout()
        other_box.addWidget(self.preset_debug_check)
        other_box.addWidget(self.preset_custom_output_check)
        right_layout.addRow("Inne opcje:", other_box)

        # 7. Folder wyjściowy
        self.preset_output_dir_edit = QLineEdit()
        self.preset_output_dir_button = QPushButton("Przeglądaj...")
        self.preset_output_dir_button.clicked.connect(self._select_preset_output_dir)
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.preset_output_dir_edit)
        output_dir_layout.addWidget(self.preset_output_dir_button)
        right_layout.addRow("Folder wyjściowy:", output_dir_layout)

        # --- Podłączenie sygnałów do auto-zapisu ---
        self.preset_script_group.buttonClicked.connect(self._save_current_preset_details)
        self.preset_ffmpeg_group.buttonClicked.connect(self._save_current_preset_details)
        self.preset_bitrate_spin.valueChanged.connect(self._save_current_preset_details)
        self.preset_subtitle_name_edit.textChanged.connect(self._save_current_preset_details)
        self.preset_movie_name_edit.textChanged.connect(self._save_current_preset_details)
        self.preset_keep_movie_name_check.toggled.connect(self._save_current_preset_details)
        self.preset_debug_check.toggled.connect(self._save_current_preset_details)
        self.preset_custom_output_check.toggled.connect(self._save_current_preset_details)

        # --- Podłączenie sygnałów do aktualizacji UI formularza ---
        self.preset_script_group.buttonClicked.connect(self._update_preset_form_state)
        self.preset_ffmpeg_group.buttonClicked.connect(self._update_preset_form_state)
        self.preset_keep_movie_name_check.toggled.connect(self._update_preset_form_state)

        # --- Dodanie paneli do splittera ---
        splitter.addWidget(left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([200, 450])

    def _load_presets_list(self):
        self.presets_list_widget.blockSignals(True)
        self.presets_list_widget.clear()
        self.settings.beginGroup("presets")
        preset_names = self.settings.childGroups()
        self.presets_list_widget.addItems(sorted(preset_names))
        self.settings.endGroup()
        self.presets_list_widget.blockSignals(False)
        self.right_panel.setEnabled(self.presets_list_widget.count() > 0)
        if self.presets_list_widget.count() > 0:
            self.presets_list_widget.setCurrentRow(0)

    def _display_preset_details(self, current_item, previous_item):
        if not current_item:
            self.right_panel.setEnabled(False)
            # Wyczyść formularz, jeśli nic nie jest zaznaczone
            for widget in self.right_panel.findChildren(QWidget):
                if isinstance(widget, QLineEdit):
                    widget.clear()
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(False)
                elif isinstance(widget, QSpinBox):
                    widget.setValue(widget.minimum())
            return

        # Zablokuj sygnały, aby uniknąć zapisu podczas wczytywania
        for widget in self.right_panel.findChildren(QWidget):
            widget.blockSignals(True)

        self.right_panel.setEnabled(True)
        preset_name = current_item.text()
        self.settings.beginGroup(f"presets/{preset_name}")

        script_id = self.settings.value("selected_script", 3, type=int)
        btn_to_check = self.preset_script_group.button(script_id)
        if btn_to_check:
            btn_to_check.setChecked(True)

        ffmpeg_id = self.settings.value("selected_ffmpeg_script", 1, type=int)
        btn_to_check = self.preset_ffmpeg_group.button(ffmpeg_id)
        if btn_to_check:
            btn_to_check.setChecked(True)

        self.preset_bitrate_spin.setValue(self.settings.value("gpu_bitrate", 8, type=int))
        self.preset_subtitle_name_edit.setText(self.settings.value("subtitle_track_name", ""))
        self.preset_movie_name_edit.setText(self.settings.value("movie_name", ""))
        self.preset_keep_movie_name_check.setChecked(self.settings.value("keep_movie_name", False, type=bool))
        self.preset_debug_check.setChecked(self.settings.value("debug_mode", False, type=bool))
        self.preset_custom_output_check.setChecked(self.settings.value("custom_output", False, type=bool))
        self.preset_output_dir_edit.setText(self.settings.value("output_dir", ""))

        self.settings.endGroup()

        # Odblokuj sygnały po wczytaniu
        for widget in self.right_panel.findChildren(QWidget):
            widget.blockSignals(False)

        # Zaktualizuj stan włącz/wyłącz kontrolek
        self._update_preset_form_state()

    def _save_current_preset_details(self):
        current_item = self.presets_list_widget.currentItem()
        if not current_item:
            return

        preset_name = current_item.text()
        self.settings.beginGroup(f"presets/{preset_name}")
        self.settings.setValue("selected_script", self.preset_script_group.checkedId())
        self.settings.setValue("selected_ffmpeg_script", self.preset_ffmpeg_group.checkedId())
        self.settings.setValue("gpu_bitrate", self.preset_bitrate_spin.value())
        self.settings.setValue("subtitle_track_name", self.preset_subtitle_name_edit.text())
        self.settings.setValue("movie_name", self.preset_movie_name_edit.text())
        self.settings.setValue("keep_movie_name", self.preset_keep_movie_name_check.isChecked())
        self.settings.setValue("debug_mode", self.preset_debug_check.isChecked())
        self.settings.setValue("custom_output", self.preset_custom_output_check.isChecked())
        self.settings.setValue("output_dir", self.preset_output_dir_edit.text())
        self.settings.endGroup()

    def _new_preset(self):
        preset_name, ok = QInputDialog.getText(self, "Nowy Preset", "Wprowadź nazwę dla nowego presetu:")
        if ok and preset_name.strip():
            name = preset_name.strip()
            self.settings.beginGroup("presets")
            if name in self.settings.childGroups():
                QMessageBox.warning(self, "Błąd", "Preset o tej nazwie już istnieje.")
                self.settings.endGroup()
                return
            self.settings.endGroup()

            # Zapisz domyślne wartości dla nowego presetu
            self.settings.beginGroup(f"presets/{name}")
            self.settings.setValue("selected_script", 3)
            self.settings.setValue("selected_ffmpeg_script", 1)
            self.settings.setValue("gpu_bitrate", 8)
            self.settings.setValue("subtitle_track_name", "")
            self.settings.setValue("movie_name", "")
            self.settings.setValue("keep_movie_name", False)
            self.settings.setValue("debug_mode", False)
            self.settings.setValue("custom_output", False)
            self.settings.setValue("output_dir", "")
            self.settings.endGroup()

            self._load_presets_list()
            # Automatycznie zaznacz nowo dodany element
            items = self.presets_list_widget.findItems(name, Qt.MatchFlag.MatchExactly)
            if items:
                self.presets_list_widget.setCurrentItem(items[0])

    def _select_preset_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder wyjściowy dla presetu", self.preset_output_dir_edit.text())
        if directory:
            self.preset_output_dir_edit.setText(directory)
            self._save_current_preset_details() # Auto-zapis po wybraniu

    def _update_preset_form_state(self):
        if not self.right_panel.isEnabled():
            return

        script_id = self.preset_script_group.checkedId()
        ffmpeg_id = self.preset_ffmpeg_group.checkedId()

        # Logika dla opcji enkodera FFmpeg
        is_ffmpeg_relevant = script_id in [1, 2, 4]
        for btn in self.preset_ffmpeg_group.buttons():
            btn.setEnabled(is_ffmpeg_relevant)

        # Logika dla bitrate
        is_gpu_encoder = ffmpeg_id in [2, 3]
        is_bitrate_relevant = (is_ffmpeg_relevant and is_gpu_encoder) or script_id == 4
        self.preset_bitrate_spin.setEnabled(is_bitrate_relevant)

        # Logika dla opcji remuxa (nazwa ścieżki, nazwa filmu)
        is_remux_relevant = script_id in [2, 3]
        self.preset_subtitle_name_edit.setEnabled(is_remux_relevant)
        self.preset_movie_name_edit.setEnabled(is_remux_relevant and not self.preset_keep_movie_name_check.isChecked())
        self.preset_keep_movie_name_check.setEnabled(is_remux_relevant)

    def _delete_preset(self):
        current_item = self.presets_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Najpierw wybierz preset do usunięcia.")
            return

        preset_name = current_item.text()
        reply = QMessageBox.question(self, "Potwierdzenie",
                                     f"Czy na pewno chcesz usunąć preset '{preset_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.settings.beginGroup("presets")
            self.settings.remove(preset_name)
            self.settings.endGroup()
            self._load_presets_list()

    def _create_processing_tab(self):
        layout = QFormLayout(self.processing_tab)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.gpu_bitrate_spin = QSpinBox()
        self.gpu_bitrate_spin.setRange(1, 100)
        self.gpu_bitrate_spin.setSuffix(" Mbps")
        layout.addRow("Domyślny bitrate dla GPU/FFmpeg + wstawka:", self.gpu_bitrate_spin)

        self.subtitle_track_name_edit = QLineEdit()
        layout.addRow("Domyślna nazwa ścieżki napisów:", self.subtitle_track_name_edit)

        self.gpu_info_label = QLabel("Wczytywanie...")
        layout.addRow("Karta graficzna:", self.gpu_info_label)

    def _create_about_tab(self):
        main_layout = QVBoxLayout(self.about_tab)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        # --- Top Section: Icon + Header ---
        self.icon_label = QLabel()
        icon = QIcon("icon/icon.svg")
        pixmap = icon.pixmap(96, 96)
        self.icon_label.setPixmap(pixmap)
        self.icon_label.setFixedWidth(100)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.icon_label.installEventFilter(self) # Instalacja filtra
        top_layout.addWidget(self.icon_label)

        top_text_label = QLabel()
        top_text_label.setTextFormat(Qt.TextFormat.RichText)
        top_text_label.setWordWrap(True)
        top_text_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        top_text_content = f"""
            <h2>Automatyzer</h2>
            <p><b>Wersja:</b> {self.app_version}</p>
            <p><b>Autor:</b> kacper12gry</p>
            <p>Inteligentny automatyzer przepływów pracy wideo. Zaprojektowany, by przyspieszyć i ułatwić zadania takie jak remux kontenerów MKV, wypalanie napisów oraz dodawanie wstawek.</p>
        """
        top_text_label.setText(top_text_content)
        top_layout.addWidget(top_text_label, 1)
        main_layout.addLayout(top_layout)

        # --- Bottom Section: Details ---
        bottom_text_label = QLabel()
        bottom_text_label.setTextFormat(Qt.TextFormat.RichText)
        bottom_text_label.setWordWrap(True)
        bottom_text_label.setOpenExternalLinks(True)

        platform_name = platform.system()
        if platform_name == "Linux":
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            platform_name = line.split("=")[1].strip().strip('\"')
                            break
            except FileNotFoundError:
                pass # Pozostanie "Linux"
        elif platform_name == "Windows":
            release_version = platform.release()
            platform_name = f"Windows {release_version}"
        elif platform_name == "Darwin":
            platform_name = "macOS"

        bottom_text_content = f"""
            <hr>
            <h4>Informacje o Systemie</h4>
            <p><b>System operacyjny:</b> {platform_name}</p>
            <hr>
            <p><b>Kod źródłowy:</b> <a href=\"https://github.com/kacper12gry/FFmpeg_gui\">https://github.com/kacper12gry/FFmpeg_gui</a></p>
        """
        bottom_text_label.setText(bottom_text_content)
        main_layout.addWidget(bottom_text_label)

        main_layout.addStretch()

    def _create_path_row(self, layout, label_text, is_file=False):
        path_edit = QLineEdit()
        browse_button = QPushButton("Przeglądaj...")
        
        widget = QWidget(self)
        hbox = QHBoxLayout(widget)
        hbox.setContentsMargins(0,0,0,0)
        hbox.addWidget(path_edit)
        hbox.addWidget(browse_button)

        if is_file:
            browse_button.clicked.connect(lambda: self._select_file(path_edit))
        else:
            browse_button.clicked.connect(lambda: self._select_directory(path_edit))

        layout.addRow(label_text, widget)
        return path_edit

    def _select_directory(self, line_edit):
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder", line_edit.text())
        if directory:
            line_edit.setText(directory)

    def _select_file(self, line_edit):
        file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik", line_edit.text())
        if file:
            line_edit.setText(file)

    def load_settings(self):
        theme_key = self.settings.value("theme", "dark", type=str)
        if theme_key in self.themes:
            self.theme_combo.setCurrentText(self.themes[theme_key])

        style_engine_key = self.settings.value("style_engine", "default", type=str)
        if style_engine_key in self.style_engines:
            self.style_engine_combo.setCurrentText(self.style_engines[style_engine_key])
        
        self.discord_rpc_checkbox.setChecked(self.settings.value("discord_rpc_enabled", False, type=bool))
        self.detailed_view_checkbox.setChecked(self.settings.value("detailed_view", False, type=bool))

        self.show_summary_checkbox.setChecked(self.settings.value("show_task_summary_confirmation", False, type=bool))

        for key, edit in self.path_edits.items():
            edit.setText(self.settings.value(key, ""))

        self.gpu_bitrate_spin.setValue(self.settings.value("processing/default_gpu_bitrate", 8, type=int))
        self.subtitle_track_name_edit.setText(self.settings.value("remux/subtitle_track_name", ""))

        self._update_style_engine_visibility(self.theme_combo.currentText())

    def save_settings(self):
        selected_theme_text = self.theme_combo.currentText()
        theme_key = next((key for key, text in self.themes.items() if text == selected_theme_text), "dark")
        self.settings.setValue("theme", theme_key)

        selected_style_text = self.style_engine_combo.currentText()
        style_key = next((key for key, text in self.style_engines.items() if text == selected_style_text), "default")
        self.settings.setValue("style_engine", style_key)

        self.settings.setValue("discord_rpc_enabled", self.discord_rpc_checkbox.isChecked())
        self.settings.setValue("detailed_view", self.detailed_view_checkbox.isChecked())

        self.settings.setValue("show_task_summary_confirmation", self.show_summary_checkbox.isChecked())

        for key, edit in self.path_edits.items():
            self.settings.setValue(key, edit.text())

        self.settings.setValue("processing/default_gpu_bitrate", self.gpu_bitrate_spin.value())
        self.settings.setValue("remux/subtitle_track_name", self.subtitle_track_name_edit.text())

        if self.parent() and hasattr(self.parent(), 'settings_changed'):
            self.parent().settings_changed = True

    def _create_diagnostics_tab(self):
        layout = QVBoxLayout(self.diagnostics_tab)

        # --- Sekcja Zależności ---
        dependencies_group = QGroupBox("Główne zależności")
        form_layout = QFormLayout(dependencies_group)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        dependencies = {
            "ffmpeg": "FFmpeg:",
            "mkvmerge": "MKVToolNix:",
            "ffprobe": "FFprobe:",
        }

        for key, label_text in dependencies.items():
            path = shutil.which(key)
            
            h_layout = QHBoxLayout()
            status_label = QLabel()
            path_edit = QLineEdit()
            path_edit.setReadOnly(True)

            if path:
                status_label.setText("✅")
                status_label.setToolTip("Znaleziono")
                path_edit.setText(path)
            else:
                status_label.setText("❌")
                status_label.setToolTip("Nie znaleziono")
                path_edit.setPlaceholderText("Brak programu w ścieżce systemowej (PATH)")
            
            h_layout.addWidget(status_label)
            h_layout.addWidget(path_edit)

            if self.is_windows and not path:
                install_button = QPushButton("Instaluj")
                if key == "ffmpeg":
                    install_button.clicked.connect(self.install_ffmpeg_winget)
                elif key == "mkvmerge":
                    install_button.clicked.connect(self.show_mkvtoolnix_instructions)
                else:
                    install_button.setVisible(False)
                h_layout.addWidget(install_button)

            form_layout.addRow(label_text, h_layout)

        layout.addWidget(dependencies_group)

        # --- Sekcja Dodatków (DLC) ---
        plugins = self.plugin_manager.get_plugins()
        if plugins:
            plugins_group = QGroupBox("Wykryte dodatki (DLC)")
            plugins_layout = QVBoxLayout(plugins_group)
            
            splitter = QSplitter(Qt.Orientation.Horizontal)

            self.plugin_list = QListWidget()
            for plugin in plugins:
                item = QListWidgetItem(plugin['name'])
                item.setData(Qt.ItemDataRole.UserRole, plugin)
                self.plugin_list.addItem(item)
            
            self.plugin_details = QTextEdit()
            self.plugin_details.setReadOnly(True)

            splitter.addWidget(self.plugin_list)
            splitter.addWidget(self.plugin_details)
            splitter.setSizes([200, 400])

            self.plugin_list.currentItemChanged.connect(self._update_plugin_details)
            if self.plugin_list.count() > 0:
                self.plugin_list.setCurrentRow(0)

            plugins_layout.addWidget(splitter)
            layout.addWidget(plugins_group)

        layout.addStretch()

    def _update_plugin_details(self, current, previous):
        if not current:
            self.plugin_details.clear()
            return

        plugin_data = current.data(Qt.ItemDataRole.UserRole)
        details_html = f"""
            <h3>{plugin_data.get('name', 'Brak nazwy')}</h3>
            <p><b>Autor:</b> {plugin_data.get('author', 'Brak danych')}</p>
            <p><b>Wersja:</b> {plugin_data.get('version', 'Brak danych')}</p>
            <hr>
            <p>{plugin_data.get('description', 'Brak opisu.')}</p>
        """
        self.plugin_details.setHtml(details_html)

    # --- Methods from DiagnosticDialog ---
    def check_dependencies(self):
        return {
            "ffmpeg": shutil.which("ffmpeg") is not None,
            "mkvmerge": shutil.which("mkvmerge") is not None,
            "ffprobe": shutil.which("ffprobe") is not None,
        }

    def install_ffmpeg_winget(self):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Instalacja FFmpeg")
        msg_box.setText("Aplikacja spróbuje zainstalować FFmpeg za pomocą menedżera pakietów Winget.\n\n"
                        "System może poprosić o uprawnienia administratora. Kontynuować?")
        yes_button = msg_box.addButton("Tak", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Nie", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)
        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            program = "winget"
            arguments = ["install", "--id=Gyan.FFmpeg", "-e", "--accept-source-agreements"]
            if self.output_window:
                self.output_window.append(">>> Rozpoczynam instalację FFmpeg przez Winget...")
            self._start_installation_process(program, arguments)
            QMessageBox.information(self, "Informacja", "Rozpoczęto instalację FFmpeg. Sprawdź postęp w głównym oknie w zakładce logów.")
            self.accept() # Close settings window

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
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle("Instrukcja instalacji MKVToolNix")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(instructions)
        msg_box.exec()
        self.accept() # Close settings window

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

    def accept(self):
        self.save_settings()
        super().accept()

    def eventFilter(self, obj, event):
        if obj is self.icon_label and event.type() == QEvent.Type.MouseButtonPress:
            self.click_counter += 1
            if self.click_counter >= 3:
                self.show_easter_egg()
                self.click_counter = 0 # Reset licznika
        return super().eventFilter(obj, event)

    def show_easter_egg(self):
        if self.image_worker and self.image_worker.isRunning():
            return # Już pobiera

        url = "https://media.discordapp.net/attachments/715984180755824662/1426229024312655912/1140298.jpg?ex=68ed19c9&is=68ebc849&hm=d1dba04faa512f0c4d80b35f399da00de7799e6bbf2bbc8e77711b32c3a1dc32&=&format=webp&width=916&height=648"
        
        self.image_worker = ImageDownloader(url, self)
        self.image_worker.image_ready.connect(self.display_easter_egg)
        self.image_worker.error_occurred.connect(self.on_image_download_error)
        self.image_worker.start()

    def display_easter_egg(self, image_data):
        signature = "Mayano Top Gun (Uma Musume: Pretty Derby)"
        dialog = EasterEggDialog(image_data, signature, self)
        dialog.exec()

    def on_image_download_error(self, error_string):
        QMessageBox.warning(self, "Błąd pobierania", f"Niespodzianki nie ma bo nie działa\n{error_string}")
