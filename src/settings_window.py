import platform
import shutil
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget, QWidget, QGroupBox, 
                             QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox, 
                             QCheckBox, QDialogButtonBox, QFileDialog, QComboBox, QHBoxLayout,
                             QMessageBox, QSplitter, QListWidget, QTextEdit, QListWidgetItem)
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
        self.processing_tab = QWidget()
        self.diagnostics_tab = QWidget()
        self.about_tab = QWidget()

        self.tabs.addTab(self.general_tab, "Ogólne")
        self.tabs.addTab(self.paths_tab, "Ścieżki")
        self.tabs.addTab(self.processing_tab, "Przetwarzanie")
        self.tabs.addTab(self.diagnostics_tab, "Diagnostyka")
        self.tabs.addTab(self.about_tab, "O Programie")

        self._create_general_tab()
        self._create_paths_tab()
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

    def _create_general_tab(self):
        layout = QFormLayout(self.general_tab)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.theme_combo = QComboBox()
        self.themes = {
            "system": "Systemowy", 
            "dark": "Ciemny", 
            "pro_light": "Jasny Profesjonalny",
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

    def _create_processing_tab(self):
        layout = QFormLayout(self.processing_tab)
        layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.gpu_bitrate_spin = QSpinBox()
        self.gpu_bitrate_spin.setRange(1, 100)
        self.gpu_bitrate_spin.setSuffix(" Mbps")
        layout.addRow("Domyślny bitrate dla GPU:", self.gpu_bitrate_spin)

        self.subtitle_track_name_edit = QLineEdit()
        layout.addRow("Domyślna nazwa ścieżki napisów:", self.subtitle_track_name_edit)

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
        QMessageBox.warning(self, "Błąd pobierania", f"Nie udało się pobrać obrazka:\n{error_string}")
