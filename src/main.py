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
    QFrame, QSizePolicy
)
from PyQt6.QtCore import QProcess, Qt, QSettings, QTimer, QUrl, QTime, QSignalBlocker
from PyQt6.QtGui import QIcon, QAction, QActionGroup, QGuiApplication, QDesktopServices, QPalette, QColor
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

from _version import __version__, latest_release_tag

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
            # --- UKŁAD ROZBUDOWANY (DASHBOARD) ---
            h_layout = QHBoxLayout()
            
            # Lewy pasek boczny
            sidebar = QVBoxLayout()
            sidebar.setSpacing(10)
            
            # 1. Główne Akcje
            actions_group = QGroupBox("Główne Akcje")
            actions_layout = QVBoxLayout(actions_group)
            self.button.setText("➕ Dodaj Zadania") 
            self.button.setMinimumHeight(45)
            self.button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self.button.setStyleSheet("font-weight: bold; font-size: 13px;")
            
            self.refresh_button.setText("🔄 Restart Programu")
            self.refresh_button.setMinimumHeight(45)
            self.refresh_button.setMaximumWidth(16777215) # Resetowanie ograniczenia (QWIDGETSIZE_MAX)
            self.refresh_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            
            actions_layout.addWidget(self.button)
            actions_layout.addWidget(self.refresh_button)
            sidebar.addWidget(actions_group)
            
            # 2. Sterowanie Kolejką
            queue_ctrl_group = QGroupBox("Sterowanie Kolejką")
            queue_grid = QVBoxLayout(queue_ctrl_group)
            
            # Przyciski przesuwania
            move_layout = QHBoxLayout()
            btn_up = QPushButton(" Góra")
            btn_up.setIcon(QIcon("icon/arrow_up.svg"))
            btn_up.clicked.connect(self.move_task_up)
            
            btn_down = QPushButton(" Dół")
            btn_down.setIcon(QIcon("icon/arrow_down.svg"))
            btn_down.clicked.connect(self.move_task_down)
            
            move_layout.addWidget(btn_up)
            move_layout.addWidget(btn_down)
            
            # Przyciski usuwania
            btn_remove = QPushButton("❌ Usuń zaznaczone")
            btn_remove.clicked.connect(self.show_cancel_confirmation)
            
            btn_clear = QPushButton("🗑️ Wyczyść wszystko")
            btn_clear.clicked.connect(self.clear_all_tasks)
            
            queue_grid.addLayout(move_layout)
            queue_grid.addWidget(btn_remove)
            queue_grid.addWidget(btn_clear)
            sidebar.addWidget(queue_ctrl_group)

            # 3. Status Aktywny
            status_group = QGroupBox("Teraz Przetwarzane")
            status_layout = QVBoxLayout(status_group)
            
            self.active_file_label = QLabel("- brak -")
            self.active_file_label.setWordWrap(True)
            self.active_file_label.setStyleSheet("font-weight: bold; color: #4aa6ff;")
            
            self.queue_active_label = QLabel("Status: Bezczynny")
            self.queue_active_label.setStyleSheet("color: gray;")
            
            status_layout.addWidget(QLabel("Plik:"))
            status_layout.addWidget(self.active_file_label)
            status_layout.addSpacing(5)
            status_layout.addWidget(self.queue_active_label)
            status_layout.addWidget(self.eta_label)
            self.eta_label.setVisible(True)
            
            sidebar.addWidget(status_group)
            
            # 4. Opcje
            settings_group = QGroupBox("Opcje")
            settings_layout = QVBoxLayout(settings_group)
            
            # Checkbox RPC
            self.rpc_dashboard_check = QCheckBox("Discord RPC")
            rpc_enabled = self.settings.value("discord_rpc_enabled", False, type=bool)
            self.rpc_dashboard_check.setChecked(rpc_enabled)
            self.rpc_dashboard_check.toggled.connect(self.toggle_discord_rpc)
            settings_layout.addWidget(self.rpc_dashboard_check)
            
            # Checkbox Szczegółowy widok
            self.detailed_dashboard_check = QCheckBox("Szczegółowy widok")
            detailed_enabled = self.settings.value("detailed_view", False, type=bool)
            self.detailed_dashboard_check.setChecked(detailed_enabled)
            self.detailed_dashboard_check.toggled.connect(self.toggle_detailed_view)
            settings_layout.addWidget(self.detailed_dashboard_check)
            
            sidebar.addWidget(settings_group)
            
            sidebar.addStretch()
            
            sidebar_widget = QWidget()
            sidebar_widget.setLayout(sidebar)
            sidebar_widget.setFixedWidth(260)
            
            h_layout.addWidget(sidebar_widget, 0)
            
            # Splitter dla logów i zadań
            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            self.splitter.addWidget(log_group)
            self.splitter.addWidget(task_group)
            self.splitter.setStretchFactor(0, 1)
            self.splitter.setStretchFactor(1, 1)
            
            h_layout.addWidget(self.splitter, 1)
            main_layout.addLayout(h_layout)

            # Timer do aktualizacji GUI
            self.dashboard_timer = QTimer(self)
            self.dashboard_timer.timeout.connect(self._update_dashboard_info)
            self.dashboard_timer.start(1000)

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

    def _update_dashboard_info(self):
        """Aktualizuje informacje w panelu bocznym."""
        if not hasattr(self, 'queue_active_label'): return
        
        is_running = self.process_manager.is_running()
        
        # Status
        status_text = "PRZETWARZANIE" if is_running else "OCZEKIWANIE"
        color = "#cf222e" if is_running else "gray" # Czerwony jeśli działa
        if not is_running and self.task_list.count() == 0:
             status_text = "BEZCZYNNY"
             color = "#2da44e" # Zielony jeśli pusto

        self.queue_active_label.setText(f"Status: {status_text}")
        self.queue_active_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        # Aktywny plik
        if self.task_list.count() > 0:
            # Zakładamy, że pierwsze zadanie jest tym aktywnym lub następnym
            item = self.task_list.item(0)
            task_name = item.text().split(" | ")[0] # Uproszczone pobieranie nazwy
            self.active_file_label.setText(task_name)
        else:
            self.active_file_label.setText("- brak zadań -")

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
        self.close()
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
    app.setApplicationName("Automatyzer")
    app.setApplicationDisplayName("Automatyzer")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("kacper12gry")
    
    original_style_name, original_stylesheet = app.style().objectName(), app.styleSheet()
    window = MainWindow(original_style_name, original_stylesheet)
    window.show()
    sys.exit(app.exec())
