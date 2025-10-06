#main.py

import sys
import os
import platform
if platform.system() == "Windows":
    import ctypes
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
    QWidget, QListWidget, QAbstractItemView, QMessageBox, QDialog,
    QGroupBox, QSplitter, QStyleFactory, QLabel
)
from PyQt6.QtCore import QProcess, Qt, QSettings
from PyQt6.QtGui import QIcon, QAction, QActionGroup, QGuiApplication

# Importy lokalnych modułów
from process_manager import ProcessManager
from component_selection_dialog import ComponentSelectionDialog
from task_manager import TaskManager
from theme_manager import get_dark_theme_qss, get_light_theme_qss, get_professional_light_theme_qss

from discord_rpc_manager import DiscordRPCManager
from plugin_manager import PluginManager
from settings_window import SettingsWindow

from _version import __version__

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

        self.create_menu_bar()
        self.load_settings()

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

    def open_settings_window(self, open_to_tab=None):
        dialog = SettingsWindow(self.settings, self.plugin_manager, self.output_window, self, version=self.app_version, is_flatpak=self.is_flatpak)
        if open_to_tab is not None:
            dialog.tabs.setCurrentIndex(open_to_tab)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if self.settings_changed:
                self.load_settings()
                self.settings_changed = False

    def open_diagnostics_tab(self):
        self.open_settings_window(open_to_tab=3)

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

    def open_component_selection_dialog(self):
        use_per_option_paths = self.use_per_option_paths_action.isChecked()
        dialog = ComponentSelectionDialog(use_per_option_paths, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.batch_tasks:
                default_subtitle_name = self.settings.value("remux/subtitle_track_name", "")
                for task_data in dialog.batch_tasks:
                    (mkv_file, subtitle_file, font_folder, selected_script,
                     selected_ffmpeg_script, gpu_bitrate, debug_mode,
                     intro_file, output_path) = task_data
                    
                    self.task_manager.add_task(
                        mkv_file, subtitle_file, font_folder,
                        selected_script, selected_ffmpeg_script,
                        gpu_bitrate, debug_mode, intro_file, output_path,
                        subtitle_track_name=default_subtitle_name,
                        movie_name=""
                    )
            else:
                self.task_manager.add_task(
                    dialog.mkv_file, dialog.subtitle_file, dialog.font_folder,
                    dialog.selected_script, dialog.selected_ffmpeg_script,
                    dialog.gpu_bitrate, dialog.debug_mode,
                    getattr(dialog, 'intro_file', None),
                    dialog.output_path,
                    subtitle_track_name=dialog.subtitle_track_name,
                    movie_name=dialog.movie_name
                )
            if not self.process_manager.is_running():
                self.process_manager.process_next_task()

    def apply_theme(self, theme_name, save=True):
        app = QApplication.instance()

        # Najpierw zresetuj do stylu Fusion, aby zapewnić czystą bazę dla arkuszy stylów
        QApplication.setStyle(QStyleFactory.create("Fusion"))

        if theme_name == "system":
            style_engine = self.settings.value("style_engine", "default", type=str)
            style_to_apply = self.original_style_name if style_engine == "default" else style_engine
            
            # Spróbuj zastosować wybrany styl, jeśli się nie uda, wróć do oryginału
            if not QStyleFactory.create(style_to_apply):
                print(f"OSTRZEŻENIE: Nie udało się załadować stylu '{style_to_apply}'. Używam domyślnego.")
                style_to_apply = self.original_style_name

            QApplication.setStyle(style_to_apply)
            app.setStyleSheet(self.original_stylesheet)

        elif theme_name == "dark":
            app.setStyleSheet(get_dark_theme_qss())
        elif theme_name == "pro_light":
            app.setStyleSheet(get_professional_light_theme_qss())
        elif theme_name == "light":
            app.setStyleSheet(get_light_theme_qss())
        
        if save:
            self.settings.setValue("theme", theme_name)
            self.settings.sync()

    def toggle_detailed_view(self, checked):
        self.task_manager.set_detailed_view(checked)
        self.settings.setValue("detailed_view", checked)
        self.settings.sync() # POPRAWKA: Wymuś zapis

    def toggle_discord_rpc(self, checked):
        if checked:
            self.rpc_manager.start()
        else:
            self.rpc_manager.stop()
        self.settings.setValue("discord_rpc_enabled", checked)
        self.settings.sync() # POPRAWKA: Wymuś zapis

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
        yes_button = msg_box.addButton("Tak", QMessageBox.ButtonRole.YesRole)
        no_button = msg_box.addButton("Nie", QMessageBox.ButtonRole.NoRole)
        msg_box.setDefaultButton(no_button)
        msg_box.exec()

        if msg_box.clickedButton() == yes_button:
            self.task_manager.remove_task(selected_row)
        if is_active:
            self.process_manager.kill_process_and_advance()
        elif not self.process_manager.is_running():
            self.process_manager.process_next_task()



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
