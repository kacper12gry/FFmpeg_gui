import sys
import os
import platform
if platform.system() == "Windows":
    import ctypes
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
                             QWidget, QListWidget, QAbstractItemView, QMessageBox, QDialog,
                             QGroupBox, QSplitter, QStyleFactory, QLabel, QListView, QMenu)
from PyQt6.QtCore import QProcess, Qt, QSettings
from PyQt6.QtGui import QIcon, QAction, QActionGroup, QGuiApplication

# Importy lokalnych modułów
from process_manager import ProcessManager
from component_selection_dialog import ComponentSelectionDialog
from task_manager import TaskManager
from theme_manager import get_dark_theme_qss, get_light_theme_qss
from diagnostic_dialog import DiagnosticDialog
from discord_rpc_manager import DiscordRPCManager
from plugin_manager import PluginManager # <-- NOWY IMPORT

class MainWindow(QMainWindow):
    def __init__(self, original_style_name, original_stylesheet):
        super().__init__()
        self.original_style_name = original_style_name
        self.original_stylesheet = original_stylesheet
        self.setWindowTitle("Automatyzer by kacper12gry")
        self.setGeometry(100, 100, 700, 500)
        self.setWindowIcon(QIcon("icon/icon.svg"))
        self.settings = QSettings("settings.ini", QSettings.Format.IniFormat)

        # Inicjalizacja PluginManagera
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.scan_for_plugins()

        self.setup_ui()
        self.rpc_manager = DiscordRPCManager(app_id='1407826664381087896')
        self.task_manager = TaskManager(self.task_list, None, self.rpc_manager)
        self.process_manager = ProcessManager(self.task_manager, self.output_window, self.rpc_manager, debug_mode=False)
        self.task_manager.process_manager = self.process_manager
        self.rpc_manager.task_manager = self.task_manager
        self.process_manager.eta_updated.connect(self.update_eta_display)

        self.create_menu_bar() # Tworzy menu po zainicjalizowaniu managera
        self.load_settings()

    def setup_ui(self):
        self.button = QPushButton("Otwórz okno wyboru komponentów", self)
        self.refresh_button = QPushButton("Odśwież", self)
        self.refresh_button.setMaximumWidth(100)
        self.output_window = QTextEdit(self); self.output_window.setReadOnly(True)
        self.task_list = QListWidget(self); self.task_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cancel_button = QPushButton("Anuluj wybrane zadanie", self)
        self.eta_label = QLabel("Czas do końca: -"); self.eta_label.setVisible(False)
        task_controls_layout = QHBoxLayout(); task_controls_layout.addWidget(self.cancel_button); task_controls_layout.addStretch(); task_controls_layout.addWidget(self.eta_label)
        button_layout = QHBoxLayout(); button_layout.addWidget(self.button); button_layout.addWidget(self.refresh_button)
        task_group = QGroupBox("Kolejka Zadań"); task_layout = QVBoxLayout(); task_layout.addWidget(self.task_list); task_layout.addLayout(task_controls_layout); task_group.setLayout(task_layout)
        log_group = QGroupBox("Log Przetwarzania"); log_layout = QVBoxLayout(); log_layout.addWidget(self.output_window); log_group.setLayout(log_layout)
        splitter = QSplitter(Qt.Orientation.Vertical); splitter.addWidget(task_group); splitter.addWidget(log_group); splitter.setStretchFactor(1, 2); splitter.setSizes([200, 300])
        main_layout = QVBoxLayout(); main_layout.addLayout(button_layout); main_layout.addWidget(splitter)
        container = QWidget(); container.setLayout(main_layout); self.setCentralWidget(container)
        self.button.clicked.connect(self.open_component_selection_dialog)
        self.refresh_button.clicked.connect(self.refresh_program)
        self.cancel_button.clicked.connect(self.show_cancel_confirmation)

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # Standardowe menu
        options_menu = menu_bar.addMenu("Opcje")
        theme_menu = options_menu.addMenu("Motyw")
        self.theme_group = QActionGroup(self); self.theme_group.setExclusive(True)
        themes = {"system": "Systemowy", "dark": "Ciemny", "light": "Fusion"}
        for key, text in themes.items():
            action = QAction(text, self, checkable=True)
            action.triggered.connect(lambda checked, k=key: self.apply_theme(k))
            self.theme_group.addAction(action)
            theme_menu.addAction(action)
        options_menu.addSeparator()
        self.detailed_view_action = QAction("Szczegółowy widok zadań", self, checkable=True)
        self.detailed_view_action.toggled.connect(self.toggle_detailed_view)
        options_menu.addAction(self.detailed_view_action)
        self.discord_rpc_action = QAction("Integracja z Discord", self, checkable=True)
        self.discord_rpc_action.toggled.connect(self.toggle_discord_rpc)
        options_menu.addAction(self.discord_rpc_action)

        # Akcja Diagnostyki
        diagnostic_action = QAction("Diagnostyka", self); diagnostic_action.triggered.connect(self.show_diagnostic_dialog)
        menu_bar.addAction(diagnostic_action)

        # --- NOWA SEKCJA: Menu DLC ---
        plugins = self.plugin_manager.get_plugins()
        if plugins:
            dlc_menu = menu_bar.addMenu("DLC")
            for plugin in plugins:
                action = QAction(plugin['name'], self)
                action.setStatusTip(plugin['description'])
                action.triggered.connect(lambda checked, p=plugin: self.plugin_manager.launch_plugin(p))
                dlc_menu.addAction(action)
        # -----------------------------

        # Akcja "O programie" zawsze na końcu
        about_action = QAction("O programie", self); about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    def load_settings(self):
        theme_name = self.settings.value("theme", "system", type=str)
        self.apply_theme(theme_name)
        actions = self.theme_group.actions()
        for action in actions:
            if action.text().lower().startswith(theme_name):
                action.setChecked(True); break
        detailed_view_enabled = self.settings.value("detailed_view", False, type=bool)
        self.detailed_view_action.setChecked(detailed_view_enabled)
        self.toggle_detailed_view(detailed_view_enabled)
        rpc_enabled = self.settings.value("discord_rpc_enabled", False, type=bool)
        self.discord_rpc_action.setChecked(rpc_enabled)
        if rpc_enabled: self.rpc_manager.start()

    def save_settings(self):
        checked_action = self.theme_group.checkedAction()
        if checked_action:
            theme_name = next(key for key, text in {"system": "Systemowy", "dark": "Ciemny", "light": "Fusion"}.items() if text == checked_action.text())
            self.settings.setValue("theme", theme_name)
        self.settings.setValue("detailed_view", self.detailed_view_action.isChecked())
        self.settings.setValue("discord_rpc_enabled", self.discord_rpc_action.isChecked())

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        if theme_name in ["dark", "light"]:
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_dark_theme_qss() if theme_name == "dark" else get_light_theme_qss())
        else:
            QApplication.setStyle(QStyleFactory.create(self.original_style_name))
            app.setStyleSheet(self.original_stylesheet)

    def toggle_detailed_view(self, checked):
        if checked:
            self.task_list.setWordWrap(True)
            self.task_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self.task_list.setUniformItemSizes(False)
            self.task_list.setResizeMode(QListView.ResizeMode.Adjust)
        else:
            self.task_list.setWordWrap(False)
            self.task_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.task_manager.set_detailed_view(checked)

    def toggle_discord_rpc(self, checked):
        if checked: self.rpc_manager.start()
        else: self.rpc_manager.stop()

    def closeEvent(self, event):
        if self.process_manager.is_running():
            reply = QMessageBox.question(self, "Potwierdzenie zamknięcia", "Aktywne zadanie jest w trakcie przetwarzania.\nCzy na pewno chcesz zamknąć program?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: event.ignore(); return
        self.save_settings(); self.process_manager.kill_process(); self.rpc_manager.stop(); super().closeEvent(event)

    def update_eta_display(self, seconds):
        if seconds < 0: self.eta_label.setVisible(False)
        else: h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60; self.eta_label.setText(f"Czas do końca: {h:02d}:{m:02d}:{s:02d}"); self.eta_label.setVisible(True)

    def show_cancel_confirmation(self):
        selected_row = self.task_list.currentRow()
        if selected_row == -1: QMessageBox.warning(self, "Uwaga", "Najpierw zaznacz zadanie na liście."); return
        task = self.task_manager.get_task(selected_row)
        if not task: return
        is_active = selected_row == 0 and self.process_manager.is_running()
        reply = QMessageBox.question(self, "Potwierdzenie", f"Czy na pewno chcesz {'przerwać aktywne' if is_active else 'usunąć'} zadanie?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes: self.task_manager.remove_task(selected_row)
        if is_active: self.process_manager.kill_process_and_advance()
        elif not self.process_manager.is_running(): self.process_manager.process_next_task()

    def open_component_selection_dialog(self):
        dialog = ComponentSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.batch_tasks:
                for task_data in dialog.batch_tasks:
                    self.task_manager.add_task(*task_data)
            else:
                self.task_manager.add_task(
                    dialog.mkv_file, dialog.subtitle_file, dialog.font_folder,
                    dialog.selected_script, dialog.selected_ffmpeg_script,
                    dialog.gpu_bitrate, dialog.debug_mode,
                    getattr(dialog, 'intro_file', None),
                    dialog.output_path
                )
            if not self.process_manager.is_running():
                self.process_manager.process_next_task()

    def show_diagnostic_dialog(self):
        # Przekazujemy plugin_manager do okna diagnostyki
        dialog = DiagnosticDialog(self.output_window, self.plugin_manager, self)
        dialog.exec()

    def show_about_dialog(self):
        platform_name = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        QMessageBox.about(self, "O programie", f"Automatyzer by kacper12gry\nVersion 4.3\n\nProgram do automatyzacji remuxowania i wypalania napisów.\n\nDziała na: {platform_name}")

    def refresh_program(self):
        self.close(); QProcess.startDetached(sys.executable, sys.argv)

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
