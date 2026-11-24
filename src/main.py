#main.py

import sys
import os
import platform
import shutil
if platform.system() == "Windows":
    import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QListWidget, QAbstractItemView, QMessageBox, QDialog,
    QGroupBox, QSplitter, QStyleFactory, QLabel, QSystemTrayIcon, QCheckBox,
    QSizePolicy, QProgressBar
)
from PyQt6.QtCore import QProcess, Qt, QSettings, QTimer, QUrl, QSignalBlocker, QSize
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QIcon, QAction, QActionGroup, QGuiApplication, QDesktopServices, QPalette, QColor, QFontDatabase
from packaging.version import parse

# Importy lokalnych modułów
from process_manager import ProcessManager
from component_selection_dialog import ComponentSelectionDialog
from task_manager import TaskManager
from theme_manager import get_dark_theme_qss, get_light_theme_qss, get_professional_light_theme_qss
from version_checker import VersionChecker

from discord_rpc_manager import DiscordRPCManager
from plugin_manager import PluginManager
from settings_window import SettingsWindow
from task_summary_dialog import TaskSummaryDialog
from command_preview_dialog import CommandPreviewDialog

from _version import __version__, latest_release_tag

def load_bundled_fonts():
    """Rejestruje czcionki z fonts_gui/: Noto Sans (interfejs) i Inconsolata (log, kolejka).
    W motywach Ciemny/Jasny są używane zawsze, więc program wygląda tak samo na każdym systemie."""
    fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts_gui")
    if os.path.isdir(fonts_dir):
        for name in sorted(os.listdir(fonts_dir)):
            if name.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(fonts_dir, name))


class MainWindow(QMainWindow):
    def __init__(self, original_style_name, original_stylesheet):
        super().__init__()
        self.app_version = __version__
        self.is_flatpak = os.path.exists('/.flatpak-info')
        self.original_style_name = original_style_name
        self.original_stylesheet = original_stylesheet
        self.setWindowTitle("Automatyzer by kacper12gry")
        self.setGeometry(100, 100, 700, 500)
        self.setWindowIcon(QIcon("icon/icon.svg"))
        self.settings = QSettings("settings.ini", QSettings.Format.IniFormat)
        self.settings_changed = False
        
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.scan_for_plugins()

        self.setup_ui()
        self.rpc_manager = DiscordRPCManager(app_id='1407826664381087896')
        self.task_manager = TaskManager(self.task_list, None, self.rpc_manager)
        self.process_manager = ProcessManager(self.task_manager, self.output_window, self.rpc_manager, debug_mode=False)
        
        self.task_manager.process_manager = self.process_manager
        self.rpc_manager.task_manager = self.task_manager
        self.process_manager.eta_updated.connect(self.update_eta_display)
        self.tray_icon = QSystemTrayIcon(QIcon("icon/icon.svg"), self)
        self.process_manager.queue_finished.connect(self.show_queue_finished_notification)

        self.create_menu_bar()
        self.load_settings()
        self.check_for_updates()
        
        # Sprawdzenie zależności przy starcie
        QTimer.singleShot(500, self._check_startup_dependencies)

    def _check_startup_dependencies(self):
        """Sprawdza czy ffmpeg, mkvmerge i ffprobe są dostępne."""
        missing = []
        for tool in ["ffmpeg", "ffprobe", "mkvmerge"]:
            if not shutil.which(tool):
                missing.append(tool)
        
        if missing:
            tools_str = ", ".join(missing)
            QMessageBox.critical(
                self, 
                "Brakujące narzędzia", 
                f"UWAGA: W Twoim systemie brakuje następujących narzędzi: <b>{tools_str}</b>.<br><br>"
                "Program może nie działać poprawnie. Zainstaluj je lub dodaj do PATH, aby móc korzystać z pełni funkcji."
            )

    def check_for_updates(self):
        if self.settings.value("update_check/enabled", True, type=bool):
            from PyQt6.QtCore import QDate
            last_check = self.settings.value("update_check/last_check_date", "", type=str)
            today = QDate.currentDate().toString(Qt.DateFormat.ISODate)

            if last_check != today:
                self.version_checker = VersionChecker(self)
                self.version_checker.check_complete.connect(self.handle_version_check_result)
                # Opcjonalnie: obsługa błędów
                # self.version_checker.error_occurred.connect(lambda e: print(f"Update check error: {e}"))
                self.version_checker.start()
                
                # Zapisujemy dzisiejszą datę jako ostatnie sprawdzenie
                self.settings.setValue("update_check/last_check_date", today)
                self.settings.sync()

    def handle_version_check_result(self, latest_version, release_url):
        ignored_versions = self.settings.value("update_check/ignored", [], type=str)

        # Użyj biblioteki packaging do niezawodnego porównywania wersji
        current_v = parse(latest_release_tag)
        latest_v = parse(latest_version)

        if latest_v > current_v and latest_version not in ignored_versions:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Dostępna nowa wersja!")
            msg_box.setTextFormat(Qt.TextFormat.RichText)
            msg_box.setText(
                f"Dostępna jest nowa wersja programu: <b>{latest_version}</b><br><br>"
                f"Czy chcesz otworzyć stronę pobierania?"
                f"<br><a href=\"{release_url}\">{release_url}</a>"
            )
            msg_box.setIcon(QMessageBox.Icon.Information)

            yes_button = msg_box.addButton("Tak", QMessageBox.ButtonRole.YesRole)
            msg_box.addButton("Nie", QMessageBox.ButtonRole.NoRole)
            msg_box.setDefaultButton(yes_button)

            checkbox = QCheckBox("Nie pokazuj ponownie dla tej wersji")
            msg_box.setCheckBox(checkbox)

            msg_box.exec()

            if msg_box.clickedButton() == yes_button:
                QDesktopServices.openUrl(QUrl(release_url))

            if checkbox.isChecked():
                ignored_versions.append(latest_version)
                self.settings.setValue("update_check/ignored", ignored_versions)

    def setup_ui(self):
        # Pobierz preferowany układ z ustawień
        self.current_layout_type = self.settings.value("ui_layout", "classic", type=str)
        
        # Dostosuj rozmiar okna do układu
        if self.current_layout_type == "dashboard":
            self.resize(1400, 800)
        else:
            self.resize(700, 500)
        
        # Główne widżety (wspólne dla obu układów)
        self.button = QPushButton("Otwórz okno wyboru komponentów", self)
        self.refresh_button = QPushButton("Odśwież", self)
        self.refresh_button.setMaximumWidth(100)
        self.output_window = QTextEdit(self)
        self.output_window.setReadOnly(True)
        self.task_list = QListWidget(self)
        self.task_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.task_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_list.customContextMenuRequested.connect(self._show_task_context_menu)
        self.cancel_button = QPushButton("Anuluj wybrane zadanie", self)
        self.eta_label = QLabel("Czas do końca: -")
        self.eta_label.setVisible(False)

        # Kontener główny
        self.main_container = QWidget()
        self.setCentralWidget(self.main_container)
        
        # Wywołaj budowanie konkretnego układu
        self._build_layout()

        # Połącz sygnały (tylko raz)
        self.button.clicked.connect(self.open_component_selection_dialog)
        self.refresh_button.clicked.connect(self.refresh_program)
        self.cancel_button.clicked.connect(self.show_cancel_confirmation)

    def _build_layout(self):
        """Buduje strukturę UI w zależności od wybranego trybu."""
        main_layout = QVBoxLayout(self.main_container)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Grupy widżetów
        task_group = QGroupBox("Kolejka Zadań")
        self.task_group = task_group
        task_layout = QVBoxLayout(task_group)
        task_layout.addWidget(self.task_list)
        
        # Kontrolki pod listą zadań
        task_controls = QHBoxLayout()
        
        # Przyciski góra/dół dla trybu klasycznego
        if self.current_layout_type != "dashboard":
            self.cancel_button.setVisible(True) # Pokaż w trybie klasycznym
            task_controls.addWidget(self.cancel_button)
            
            # Przyciski góra/dół (Ikony) - Po prawej stronie przycisku anuluj
            btn_up = QPushButton()
            btn_up.setIcon(QIcon("icon/arrow_up.svg"))
            btn_up.setToolTip("Przesuń wyżej")
            btn_up.setFixedWidth(30)
            btn_up.clicked.connect(self.move_task_up)
            
            btn_down = QPushButton()
            btn_down.setIcon(QIcon("icon/arrow_down.svg"))
            btn_down.setToolTip("Przesuń niżej")
            btn_down.setFixedWidth(30)
            btn_down.clicked.connect(self.move_task_down)
            
            task_controls.addWidget(btn_up)
            task_controls.addWidget(btn_down)
        else:
            self.cancel_button.setVisible(False) # Ukryj w Dashboardzie (bo lewituje)

        task_controls.addStretch()
        task_controls.addWidget(self.eta_label)
        task_layout.addLayout(task_controls)

        log_group = QGroupBox("Log Przetwarzania")
        log_layout = QVBoxLayout(log_group)
        log_layout.addWidget(self.output_window)

        if self.current_layout_type == "dashboard":
            # --- UKŁAD PANELU STEROWANIA ---
            # Góra: karta "Teraz przetwarzane" na całą szerokość (+ główna akcja).
            # Dół: kolejka (z paskiem przycisków) | log. Opcje są w menu "Opcje".
            # QGroupBox jak "Kolejka" i "Log" - natywna ramka w każdym stylu systemowym (też Breeze)
            card = QGroupBox("Teraz przetwarzane")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 6, 14, 10)
            card_layout.setSpacing(6)

            top_row = QHBoxLayout()
            self.queue_active_label = QLabel()
            self.active_file_label = QLabel()
            self.active_file_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
            # Długa nazwa pliku nie rozpycha okna (pełna ścieżka w podpowiedzi)
            self.active_file_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            top_row.addWidget(self.queue_active_label)
            top_row.addSpacing(8)
            top_row.addWidget(self.active_file_label, 1)

            self.refresh_button.setText("")   # ikona z icon/restart*.svg (wariant wg motywu)
            self.refresh_button.setIconSize(QSize(20, 20))
            self._restart_icon_button = self.refresh_button
            self.refresh_button.setToolTip("Restart programu")
            self.refresh_button.setFixedWidth(44)
            self.refresh_button.setProperty("variant", "secondary")
            self.button.setText("Dodaj zadania")   # ikona z icon/plus*.svg (wariant wg motywu)
            self.button.setIconSize(QSize(16, 16))
            self._add_icon_button = self.button
            self.button.setMinimumWidth(160)
            self.button.setDefault(True)   # natywne wyróżnienie głównej akcji (Breeze/Fusion/Windows)
            top_row.addWidget(self.refresh_button)
            top_row.addWidget(self.button)
            card_layout.addLayout(top_row)

            self.active_step_label = QLabel()
            self._make_muted(self.active_step_label)
            card_layout.addWidget(self.active_step_label)

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat("%p%")
            self.progress_bar.setFixedHeight(22)
            card_layout.addWidget(self.progress_bar)

            stats_row = QHBoxLayout()
            self.speed_label = QLabel()
            self._make_muted(self.speed_label)
            stats_row.addWidget(self.speed_label)
            stats_row.addStretch()
            stats_row.addWidget(self.eta_label)
            card_layout.addLayout(stats_row)

            main_layout.addWidget(card)

            # Pasek przycisków nad listą zadań
            toolbar = QHBoxLayout()
            btn_up = QPushButton("▲ Wyżej")
            btn_up.setProperty("variant", "secondary")
            btn_up.clicked.connect(self.move_task_up)
            btn_down = QPushButton("▼ Niżej")
            btn_down.setProperty("variant", "secondary")
            btn_down.clicked.connect(self.move_task_down)
            btn_remove = QPushButton("Usuń")
            btn_remove.setToolTip("Usuń zaznaczone zadanie (aktywne zostanie przerwane)")
            btn_remove.setProperty("variant", "danger")
            btn_remove.clicked.connect(self.show_cancel_confirmation)
            btn_clear = QPushButton("Wyczyść")
            btn_clear.setToolTip("Usuń wszystkie oczekujące zadania")
            btn_clear.setProperty("variant", "danger")
            btn_clear.clicked.connect(self.clear_all_tasks)
            toolbar.addWidget(btn_up)
            toolbar.addWidget(btn_down)
            toolbar.addStretch()
            toolbar.addWidget(btn_remove)
            toolbar.addWidget(btn_clear)
            task_group.layout().insertLayout(0, toolbar)
            self._danger_buttons = [btn_remove, btn_clear]
            self._refresh_native_accents()

            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            self.splitter.addWidget(task_group)
            self.splitter.addWidget(log_group)
            self.splitter.setStretchFactor(0, 3)
            self.splitter.setStretchFactor(1, 2)
            saved_split = self.settings.value("dashboard_splitter_v2")
            if saved_split is not None:
                self.splitter.restoreState(saved_split)
            self.splitter.splitterMoved.connect(
                lambda *_: self.settings.setValue("dashboard_splitter_v2", self.splitter.saveState()))
            main_layout.addWidget(self.splitter, 1)

            self.dashboard_timer = QTimer(self)
            self.dashboard_timer.timeout.connect(self._update_dashboard_info)
            self.dashboard_timer.start(500)

        else:
            # --- UKŁAD KLASYCZNY ---
            self.button.setText("Otwórz okno wyboru komponentów")
            button_layout = QHBoxLayout()
            button_layout.addWidget(self.button)
            button_layout.addWidget(self.refresh_button)
            main_layout.addLayout(button_layout)

            self.splitter = QSplitter(Qt.Orientation.Vertical)
            self.splitter.addWidget(task_group)
            self.splitter.addWidget(log_group)
            self.splitter.setStretchFactor(1, 2)
            main_layout.addWidget(self.splitter)

    def _make_muted(self, label):
        """Tekst pomocniczy: w motywach programu kolor z QSS, w systemowym z palety systemu."""
        label.setProperty("muted", True)
        self.__dict__.setdefault("_muted_labels", []).append(label)

    def _refresh_native_accents(self):
        """Czerwony tekst przycisków Usuń/Wyczyść dopasowany do jasnej/ciemnej palety systemu.
        W motywach Ciemny/Jasny i tak nadpisuje go arkusz stylów."""
        # Arkusz stylów (Ciemny/Jasny) ustawia kolor przez QLabel[muted]; bez niego bierzemy
        # przygaszony kolor z palety systemu (PlaceholderText).
        has_qss = bool(QApplication.instance().styleSheet())
        role = QPalette.ColorRole.WindowText if has_qss else QPalette.ColorRole.PlaceholderText
        for label in getattr(self, "_muted_labels", []):
            label.setForegroundRole(role)

        # Ikony SVG z folderu icon/: "nazwa.svg" = biała (ciemne tło), "nazwa_dark.svg" = ciemna (jasne tło)
        theme = getattr(self, "_current_theme", "system")
        palette_is_dark = QApplication.palette().color(QPalette.ColorRole.Button).lightness() < 128
        restart_btn = getattr(self, "_restart_icon_button", None)
        if restart_btn is not None:
            light_glyph = theme == "dark" or (theme not in ("dark", "pro_light") and palette_is_dark)
            restart_btn.setIcon(QIcon("icon/restart.svg" if light_glyph else "icon/restart_dark.svg"))
        add_btn = getattr(self, "_add_icon_button", None)
        if add_btn is not None:
            # Motywy programu: kolorowy przycisk z białym tekstem -> biały plus
            light_glyph = theme in ("dark", "pro_light") or palette_is_dark
            add_btn.setIcon(QIcon("icon/plus.svg" if light_glyph else "icon/plus_dark.svg"))

        buttons = getattr(self, "_danger_buttons", [])
        if not buttons:
            return
        is_dark = QApplication.palette().color(QPalette.ColorRole.Window).lightness() < 128
        color = QColor("#ff7b72" if is_dark else "#B42318")
        for btn in buttons:
            pal = btn.palette()
            pal.setColor(QPalette.ColorRole.ButtonText, color)
            btn.setPalette(pal)

    def _update_dashboard_info(self):
        """Aktualizuje panel boczny i licznik kolejki (układ panelu sterowania)."""
        if not hasattr(self, 'queue_active_label') or not hasattr(self, 'process_manager'): return

        pm = self.process_manager
        count = len(self.task_manager.tasks)
        self.task_group.setTitle(f"Kolejka zadań ({count})" if count else "Kolejka zadań")

        is_running = pm.is_running()
        task = self.task_manager.get_task(0)

        if is_running and task:
            state, color = "● Przetwarzanie", "#E67E22"
        elif count:
            state, color = "● Oczekiwanie", "gray"
        else:
            state, color = "● Bezczynny", "#2da44e"
        self.queue_active_label.setText(state)
        self.queue_active_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        if task and task.mkv_file:
            self.active_file_label.setText(task.mkv_file.name)
            self.active_file_label.setToolTip(str(task.mkv_file))
        else:
            self.active_file_label.setText("Brak zadań - kliknij „Dodaj zadania”, aby zacząć")
            self.active_file_label.setToolTip("")

        self.active_step_label.setText(task.status if (task and is_running) else "")
        self.active_step_label.setVisible(bool(task and is_running))

        # Postęp: procent z FFmpeg; mkvmerge/ffprobe nie podają procentu -> pasek "w toku"
        self.progress_bar.setVisible(is_running)
        if is_running:
            if pm.progress_percentage is not None and pm.progress_percentage >= 0:
                if self.progress_bar.maximum() == 0:
                    self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(min(100, int(pm.progress_percentage)))
            else:
                self.progress_bar.setRange(0, 0)

        speed = pm.current_ffmpeg_speed
        self.speed_label.setText(f"Prędkość: {speed}" if (is_running and speed) else "")
        self.progress_bar.setVisible(is_running)
        self.speed_label.setVisible(bool(is_running and speed))
        if not is_running:
            self.eta_label.setVisible(False)

    def _show_task_context_menu(self, pos):
        row = self.task_list.indexAt(pos).row()
        if row < 0:
            return
        self.task_list.setCurrentRow(row)
        menu = QMenu(self)
        preview_action = menu.addAction("Podgląd komendy...")
        if menu.exec(self.task_list.viewport().mapToGlobal(pos)) == preview_action:
            self.show_command_preview(row)

    def show_command_preview(self, row):
        task = self.task_manager.get_task(row)
        if not task:
            return
        steps = self.process_manager.build_command_preview(task)
        CommandPreviewDialog(steps, self).exec()

    def move_task_up(self):
        row = self.task_list.currentRow()
        if row <= 0: return # Nie można wyżej

        # Zabezpieczenie: Jeśli proces działa, nie pozwól ruszać zadania nr 0 ani wstawiać przed nie
        if self.process_manager.is_running():
            if row == 0:
                QMessageBox.warning(self, "Blokada", "Nie można przesuwać zadania, które jest aktualnie przetwarzane.")
                return
            if row == 1:
                QMessageBox.warning(self, "Blokada", "Nie można wstawić zadania przed aktualnie przetwarzane.")
                return

        # Zlecamy przesunięcie managerowi (on odświeży widok)
        self.task_manager.move_task(row, row - 1)
        
        # Przywracamy zaznaczenie na przesunięty element
        self.task_list.setCurrentRow(row - 1)

    def move_task_down(self):
        row = self.task_list.currentRow()
        if row == -1 or row >= self.task_list.count() - 1: return # Nie można niżej

        # Zabezpieczenie: Jeśli proces działa, nie pozwól ruszać zadania nr 0
        if self.process_manager.is_running() and row == 0:
            QMessageBox.warning(self, "Blokada", "Nie można przesuwać zadania, które jest aktualnie przetwarzane.")
            return

        # Zlecamy przesunięcie managerowi
        self.task_manager.move_task(row, row + 1)
        
        # Przywracamy zaznaczenie
        self.task_list.setCurrentRow(row + 1)

    def clear_all_tasks(self):
        if self.task_list.count() == 0:
            return

        msg = "Czy na pewno usunąć WSZYSTKIE zadania?"
        if self.process_manager.is_running():
            msg = "Proces jest aktywny. Zostaną usunięte tylko zadania oczekujące (kolejka).\nZadanie obecnie przetwarzane pozostanie.\n\nCzy kontynuować?"

        reply = QMessageBox.question(self, "Potwierdzenie", msg, 
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.process_manager.is_running():
                # Usuń wszystko poza indeksem 0 (aktywnym)
                # Iterujemy tak długo, jak długo są więcej niż 1 zadanie
                while self.task_list.count() > 1:
                    # Zawsze usuwamy indeks 1, bo lista się przesuwa po usunięciu
                    self.task_manager.remove_task(1)
                
                QMessageBox.information(self, "Info", "Wyczyszczono kolejkę oczekujących zadań.")
            else:
                self.task_list.clear()
                self.task_manager.tasks.clear()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        options_menu = menu_bar.addMenu("Opcje")

        settings_action = QAction("Ustawienia...", self)
        settings_action.triggered.connect(self.open_settings_window)
        options_menu.addAction(settings_action)
        options_menu.addSeparator()

        layout_menu = options_menu.addMenu("Układ")
        self.layout_group = QActionGroup(self)
        classic_action = QAction("Klasyczny (Pionowy)", self, checkable=True)
        dashboard_action = QAction("Panel sterowania (Poziomy)", self, checkable=True)
        
        curr_layout = self.settings.value("ui_layout", "classic", type=str)
        classic_action.setChecked(curr_layout == "classic")
        dashboard_action.setChecked(curr_layout == "dashboard")
        
        classic_action.triggered.connect(lambda: self.change_layout("classic"))
        dashboard_action.triggered.connect(lambda: self.change_layout("dashboard"))
        
        self.layout_group.addAction(classic_action)
        self.layout_group.addAction(dashboard_action)
        layout_menu.addAction(classic_action)
        layout_menu.addAction(dashboard_action)

        theme_menu = options_menu.addMenu("Motyw")
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.themes = {"system": "Systemowy", "dark": "Ciemny", "pro_light": "Jasny", "light": "Fusion"}
        for key, text in self.themes.items():
            action = QAction(text, self, checkable=True)
            action.triggered.connect(lambda checked, k=key: self.apply_theme(k))
            self.theme_group.addAction(action)
            theme_menu.addAction(action)
        options_menu.addSeparator()

        self.use_per_option_paths_action = QAction("Używaj niestandardowych ścieżek dla opcji", self, checkable=True)
        self.use_per_option_paths_action.toggled.connect(lambda checked: (self.settings.setValue("use_per_option_paths", checked), self.settings.sync()))
        options_menu.addAction(self.use_per_option_paths_action)
        options_menu.addSeparator()

        self.detailed_view_action = QAction("Szczegółowy widok zadań", self, checkable=True)
        self.detailed_view_action.toggled.connect(self.toggle_detailed_view)
        options_menu.addAction(self.detailed_view_action)

        self.discord_rpc_action = QAction("Integracja z Discord", self, checkable=True)
        self.discord_rpc_action.toggled.connect(self.toggle_discord_rpc)
        self.discord_rpc_action.setVisible(not self.is_flatpak)
        options_menu.addAction(self.discord_rpc_action)

        diagnostic_action = QAction("Diagnostyka", self)
        diagnostic_action.triggered.connect(self.open_diagnostics_tab)
        menu_bar.addAction(diagnostic_action)

        plugins = self.plugin_manager.get_plugins()
        if plugins:
            dlc_menu = menu_bar.addMenu("DLC")
            for plugin in plugins:
                action = QAction(plugin['name'], self)
                action.setStatusTip(plugin['description'])
                action.triggered.connect(lambda checked, p=plugin: self.plugin_manager.launch_plugin(p))
                dlc_menu.addAction(action)

        about_action = QAction("O programie", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    def open_settings_window(self, open_to_tab=None, open_to_tab_name=None):
        dialog = SettingsWindow(self.settings, self.plugin_manager, self.output_window, self, version=self.app_version, is_flatpak=self.is_flatpak)
        if open_to_tab is not None:
            dialog.tabs.setCurrentIndex(open_to_tab)
        elif open_to_tab_name is not None:
            dialog.open_tab_by_name(open_to_tab_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.settings_changed:
                self.load_settings()
                self.settings_changed = False

    def open_diagnostics_tab(self):
        self.open_settings_window(open_to_tab_name="Diagnostyka")

    def load_settings(self):
        theme_name = self.settings.value("theme", "dark", type=str)
        self.apply_theme(theme_name, save=False)
        for action in self.theme_group.actions():
            if self.themes.get(theme_name) == action.text():
                action.setChecked(True)
                break

        use_paths_enabled = self.settings.value("use_per_option_paths", False, type=bool)
        self.use_per_option_paths_action.setChecked(use_paths_enabled)

        detailed_view_enabled = self.settings.value("detailed_view", False, type=bool)
        self.detailed_view_action.setChecked(detailed_view_enabled)

        rpc_enabled = self.settings.value("discord_rpc_enabled", False, type=bool)
        self.discord_rpc_action.setChecked(rpc_enabled)

    def _update_setting(self, key, value, callback=None):
        """
        Metoda pomocnicza do aktualizacji ustawienia, zapisania go i opcjonalnego wywołania funkcji zwrotnej.
        """
        self.settings.setValue(key, value)
        self.settings.sync()
        if callback:
            callback(value)

    def open_component_selection_dialog(self):
        use_per_option_paths = self.use_per_option_paths_action.isChecked()
        dialog = ComponentSelectionDialog(use_per_option_paths, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            show_summary = self.settings.value("show_task_summary_confirmation", False, type=bool)

            tasks_to_add = dialog.tasks_to_return # Pobierz ujednoliconą listę zadań

            if tasks_to_add: # Sprawdź, czy są jakieś zadania do dodania
                # Obsłuż okno podsumowania tylko dla pojedynczych zadań, jeśli jest włączone
                if len(tasks_to_add) == 1 and show_summary:
                    summary_dialog = TaskSummaryDialog(tasks_to_add[0], self) # Przekaż słownik pojedynczego zadania
                    if summary_dialog.exec() == QDialog.DialogCode.Accepted:
                        for task_data in tasks_to_add:
                            self.task_manager.add_task(**task_data)
                else: # Dodaj wszystkie zadania bezpośrednio (wsadowe lub pojedyncze bez podsumowania)
                    for task_data in tasks_to_add:
                        self.task_manager.add_task(**task_data)

            if not self.process_manager.is_running():
                self.process_manager.process_next_task()

    def apply_theme(self, theme_name, save=True):
        app = QApplication.instance()
        self._current_theme = theme_name

        # Ustaw styl i arkusz stylów
        if theme_name == "system":
            style_engine = self.settings.value("style_engine", "default", type=str)
            style_to_apply = self.original_style_name if style_engine == "default" else style_engine
            if not QStyleFactory.create(style_to_apply):
                style_to_apply = self.original_style_name
            QApplication.setStyle(style_to_apply)
            app.setStyleSheet(self.original_stylesheet)
        elif theme_name == "dark":
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_dark_theme_qss())
            self._update_windows_titlebar(dark_mode=True)
        elif theme_name == "pro_light":
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_professional_light_theme_qss())
            self._update_windows_titlebar(dark_mode=False)
        elif theme_name == "light":
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_light_theme_qss())
            self._update_windows_titlebar(dark_mode=False)

        self._refresh_native_accents()

        # Zapisz ustawienie
        if save:
            self.settings.setValue("theme", theme_name)
            self.settings.sync()

    def _update_windows_titlebar(self, dark_mode=True):
        """Wymusza ciemny/jasny pasek tytułu na Windows."""
        if platform.system() != "Windows": return
        try:
            import ctypes
            hwnd = int(self.winId())
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1 if dark_mode else 0)), 4)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
        except Exception: pass

    def toggle_detailed_view(self, checked):
        self._update_setting("detailed_view", checked, self.task_manager.set_detailed_view)
        
        # Synchronizacja checkboxa w Dashboardzie
        if hasattr(self, 'detailed_dashboard_check') and self.detailed_dashboard_check.isChecked() != checked:
            with QSignalBlocker(self.detailed_dashboard_check):
                self.detailed_dashboard_check.setChecked(checked)
        
        # Synchronizacja akcji w menu
        if hasattr(self, 'detailed_view_action') and self.detailed_view_action.isChecked() != checked:
            with QSignalBlocker(self.detailed_view_action):
                self.detailed_view_action.setChecked(checked)

    def toggle_discord_rpc(self, checked):
        if checked:
            self.rpc_manager.start()
        else:
            self.rpc_manager.stop()
        
        self._update_setting("discord_rpc_enabled", checked)
        
        # Synchronizacja UI (blokada sygnałów, aby uniknąć pętli)
        if hasattr(self, 'discord_rpc_action') and self.discord_rpc_action.isChecked() != checked:
            with QSignalBlocker(self.discord_rpc_action):
                self.discord_rpc_action.setChecked(checked)
        
        if hasattr(self, 'rpc_dashboard_check') and self.rpc_dashboard_check.isChecked() != checked:
            with QSignalBlocker(self.rpc_dashboard_check):
                self.rpc_dashboard_check.setChecked(checked)

    def closeEvent(self, event):
        if hasattr(self, 'process_manager') and self.process_manager.is_running():
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle("Potwierdzenie zamknięcia")
            msg_box.setText("Aktywne zadanie jest w trakcie przetwarzania.\nCzy na pewno chcesz zamknąć program?")
            msg_box.addButton("Tak", QMessageBox.ButtonRole.YesRole)
            no_button = msg_box.addButton("Nie", QMessageBox.ButtonRole.NoRole)
            msg_box.setDefaultButton(no_button)
            msg_box.exec()

            if msg_box.clickedButton() == no_button:
                event.ignore()
                return

        # Szybkie czyszczenie zasobów
        if hasattr(self, 'version_checker') and self.version_checker.isRunning():
            self.version_checker.quit()
            self.version_checker.wait(500) # Max 0.5s na zamknięcie sieci

        if hasattr(self, 'process_manager'):
            self.process_manager.kill_process()
            
        if hasattr(self, 'rpc_manager'):
            self.rpc_manager.stop()
            
        super().closeEvent(event)

    def update_eta_display(self, seconds):
        if seconds < 0:
            self.eta_label.setVisible(False)
        else:
            h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
            self.eta_label.setText(f"Czas do końca: {h:02d}:{m:02d}:{s:02d}")
            self.eta_label.setVisible(True)

    def show_cancel_confirmation(self):
        selected_row = self.task_list.currentRow()
        if selected_row == -1:
            QMessageBox.warning(self, "Uwaga", "Najpierw zaznacz zadanie na liście.")
            return
        task = self.task_manager.get_task(selected_row)
        if not task:
            return
        is_active = selected_row == 0 and self.process_manager.is_running()

        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle("Potwierdzenie")
        msg_box.setText(f"Czy na pewno chcesz {'przerwać aktywne' if is_active else 'usunąć'} zadanie?")
        msg_box.addButton("Tak", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Nie", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)
        msg_box.exec()

        if msg_box.clickedButton() == no_button:
            return

        self.task_manager.remove_task(selected_row)
        if is_active:
            self.process_manager.kill_process_and_advance()
        elif not self.process_manager.is_running():
            self.process_manager.process_next_task()

    def show_queue_finished_notification(self):
        self.tray_icon.show()
        self.tray_icon.showMessage(
            "Automatyzer - Zakończono",
            "Wszystkie zadania w kolejce zostały ukończone.",
            QSystemTrayIcon.MessageIcon.Information,
            5000 # Czas wyświetlania w milisekundach
        )
        # Użyj timera, aby ukryć ikonę po chwili
        QTimer.singleShot(6000, self.tray_icon.hide)


    def show_about_dialog(self):
        platform_name = "Nieznany"
        if platform.system() == "Windows":
            platform_name = "Windows"
        elif platform.system() == "Linux":
            platform_name = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        elif platform.system() == "Darwin":
            platform_name = "macOS"

        QMessageBox.about(self, "O programie", f"Automatyzer by kacper12gry\nVersion {self.app_version}\n\nInteligentny automatyzer przepływów pracy wideo.\nZaprojektowany, by przyspieszyć i ułatwić zadania takie jak remux kontenerów MKV, wypalanie napisów oraz dodawanie wstawek.\n\nDziała na: {platform_name}")

    def refresh_program(self):
        if self.close():   # close() zwraca False, gdy użytkownik anulował zamknięcie
            QProcess.startDetached(sys.executable, sys.argv)

    def change_layout(self, layout_type):
        """Zmienia typ układu i informuje o konieczności restartu."""
        if self.current_layout_type == layout_type:
            return
            
        self.settings.setValue("ui_layout", layout_type)
        self.settings.sync()
        
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Zmiana układu")
        msg.setText("Zmiana układu interfejsu wymaga ponownego uruchomienia programu.")
        restart_btn = msg.addButton("Uruchom ponownie teraz", QMessageBox.ButtonRole.AcceptRole)
        msg.addButton("Później", QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        
        if msg.clickedButton() == restart_btn:
            self.refresh_program()

if __name__ == "__main__":
    QGuiApplication.setDesktopFileName('pl.com.github.kacper12gry.automatyzer')
    if platform.system() == "Windows":
        myappid = 'com.github.kacper12gry.automatyzer'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    load_bundled_fonts()
    app.setApplicationName("Automatyzer")
    app.setApplicationDisplayName("Automatyzer")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("kacper12gry")
    
    original_style_name, original_stylesheet = app.style().objectName(), app.styleSheet()
    window = MainWindow(original_style_name, original_stylesheet)
    window.show()
    sys.exit(app.exec())
