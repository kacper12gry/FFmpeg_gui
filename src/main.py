#main.py

import sys
import os
import platform
if platform.system() == "Windows":
    import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QListWidget, QAbstractItemView, QMessageBox, QDialog,
    QGroupBox, QSplitter, QStyleFactory, QLabel, QSystemTrayIcon, QCheckBox
)
from PyQt6.QtCore import QProcess, Qt, QSettings, QTimer, QUrl
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

    def check_for_updates(self):
        if self.settings.value("update_check/enabled", True, type=bool):
            self.version_checker = VersionChecker(self)
            self.version_checker.check_complete.connect(self.handle_version_check_result)
            # Opcjonalnie: obsługa błędów
            # self.version_checker.error_occurred.connect(lambda e: print(f"Update check error: {e}"))
            self.version_checker.start()

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
        task_controls_layout = QHBoxLayout()
        task_controls_layout.addWidget(self.cancel_button)
        task_controls_layout.addStretch()
        task_controls_layout.addWidget(self.eta_label)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button)
        button_layout.addWidget(self.refresh_button)
        task_group = QGroupBox("Kolejka Zadań")
        task_layout = QVBoxLayout()
        task_layout.addWidget(self.task_list)
        task_layout.addLayout(task_controls_layout)
        task_group.setLayout(task_layout)
        log_group = QGroupBox("Log Przetwarzania")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self.output_window)
        log_group.setLayout(log_layout)
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(task_group)
        splitter.addWidget(log_group)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([200, 300])
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(splitter)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.button.clicked.connect(self.open_component_selection_dialog)
        self.refresh_button.clicked.connect(self.refresh_program)
        self.cancel_button.clicked.connect(self.show_cancel_confirmation)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        options_menu = menu_bar.addMenu("Opcje")

        settings_action = QAction("Ustawienia...", self)
        settings_action.triggered.connect(self.open_settings_window)
        options_menu.addAction(settings_action)
        options_menu.addSeparator()

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

        # Ustaw paletę kolorów
        if theme_name == "dark":
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#2b2b2b"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0e0e0"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#E67E22"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            app.setPalette(palette)
        elif theme_name == "pro_light":
            palette = QPalette()
            palette.setColor(QPalette.ColorRole.Window, QColor("#F0F0F0"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#111111"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#0078D4"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            app.setPalette(palette)
        else:
            # Dla motywów 'system' i 'light', przywróć domyślną paletę
            original_style = QStyleFactory.create(self.original_style_name)
            if original_style:
                app.setPalette(original_style.standardPalette())

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
        elif theme_name == "pro_light":
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_professional_light_theme_qss())
        elif theme_name == "light":
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_light_theme_qss())

        # Zapisz ustawienie
        if save:
            self.settings.setValue("theme", theme_name)
            self.settings.sync()

    def toggle_detailed_view(self, checked):
        self._update_setting("detailed_view", checked, self.task_manager.set_detailed_view)

    def toggle_discord_rpc(self, checked):
        if checked:
            self.rpc_manager.start()
        else:
            self.rpc_manager.stop()
        self._update_setting("discord_rpc_enabled", checked)

    def closeEvent(self, event):
        if self.process_manager.is_running():
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
        self.process_manager.kill_process()
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

if __name__ == "__main__":
    QGuiApplication.setDesktopFileName('pl.com.github.kacper12gry.automatyzer')
    if platform.system() == "Windows":
        myappid = 'com.github.kacper12gry.automatyzer'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    original_style_name, original_stylesheet = app.style().objectName(), app.styleSheet()
    window = MainWindow(original_style_name, original_stylesheet)
    window.show()
    sys.exit(app.exec())
