# main.py
import sys
import os
import platform

if platform.system() == "Windows":
    import ctypes

from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout,
                             QWidget, QListWidget, QAbstractItemView, QMessageBox, QDialog,
                             QGroupBox, QSplitter, QStyleFactory, QLabel)
from PyQt6.QtCore import QProcess, Qt, QSettings
from PyQt6.QtGui import QIcon, QAction, QActionGroup, QGuiApplication

from process_manager import ProcessManager
from component_selection_dialog import ComponentSelectionDialog
from task_manager import TaskManager
from theme_manager import get_dark_theme_qss, get_light_theme_qss
from diagnostic_dialog import DiagnosticDialog

class MainWindow(QMainWindow):
    def __init__(self, original_style_name, original_stylesheet):
        super().__init__()
        self.original_style_name = original_style_name
        self.original_stylesheet = original_stylesheet
        self.setWindowTitle("Automatyzer by kacper12gry")
        self.setGeometry(100, 100, 700, 500)
        self.setWindowIcon(QIcon("icon/icon.svg"))

        self.setup_ui()

        self.process_manager = ProcessManager(None, self.output_window, debug_mode=False)
        # POPRAWKA: Przekazujemy process_manager do TaskManagera
        self.task_manager = TaskManager(self.task_list, self.process_manager)
        self.process_manager.task_manager = self.task_manager # Uzupełniamy referencję

        self.process_manager.eta_updated.connect(self.update_eta_display)

        self.create_menu_bar()
        self.load_settings()

    def setup_ui(self):
        # ... (bez zmian)
        self.button = QPushButton("Otwórz okno wyboru komponentów", self)
        self.refresh_button = QPushButton("Odśwież", self)
        self.refresh_button.setMaximumWidth(100)
        self.output_window = QTextEdit(self); self.output_window.setReadOnly(True)
        self.task_list = QListWidget(self); self.task_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cancel_button = QPushButton("Anuluj wybrane zadanie", self)
        self.eta_label = QLabel("Czas do końca: -"); self.eta_label.setVisible(False)
        task_controls_layout = QHBoxLayout()
        task_controls_layout.addWidget(self.cancel_button); task_controls_layout.addStretch(); task_controls_layout.addWidget(self.eta_label)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button); button_layout.addWidget(self.refresh_button)
        task_group = QGroupBox("Kolejka Zadań")
        task_layout = QVBoxLayout(); task_layout.addWidget(self.task_list); task_layout.addLayout(task_controls_layout)
        task_group.setLayout(task_layout)
        log_group = QGroupBox("Log Przetwarzania")
        log_layout = QVBoxLayout(); log_layout.addWidget(self.output_window)
        log_group.setLayout(log_layout)
        splitter = QSplitter(Qt.Orientation.Vertical); splitter.addWidget(task_group); splitter.addWidget(log_group)
        splitter.setStretchFactor(1, 2); splitter.setSizes([200, 300])
        main_layout = QVBoxLayout(); main_layout.addLayout(button_layout); main_layout.addWidget(splitter)
        container = QWidget(); container.setLayout(main_layout); self.setCentralWidget(container)
        self.button.clicked.connect(self.open_component_selection_dialog)
        self.refresh_button.clicked.connect(self.refresh_program)
        self.cancel_button.clicked.connect(self.show_cancel_confirmation)

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # Menu "Motyw"
        theme_menu = menu_bar.addMenu("Motyw")
        self.theme_group = QActionGroup(self); self.theme_group.setExclusive(True)
        actions = {"system": "Systemowy", "dark": "Ciemny", "light": "Fusion"}
        self.theme_actions = {}
        for key, text in actions.items():
            action = QAction(text, self, checkable=True)
            action.triggered.connect(lambda checked, k=key: self.apply_theme(k))
            theme_menu.addAction(action)
            self.theme_group.addAction(action)
            self.theme_actions[key] = action

        # POPRAWKA: Nowe menu "Opcje"
        options_menu = menu_bar.addMenu("Opcje")
        self.detailed_view_action = QAction("Szczegółowy widok zadań", self, checkable=True)
        self.detailed_view_action.triggered.connect(self.toggle_detailed_view)
        options_menu.addAction(self.detailed_view_action)

        # Pozostałe menu
        diagnostic_action = QAction("Diagnostyka", self); diagnostic_action.triggered.connect(self.show_diagnostic_dialog)
        menu_bar.addAction(diagnostic_action)
        about_action = QAction("O programie", self); about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    # NOWA METODA: Obsługa przełącznika widoku
    def toggle_detailed_view(self, checked):
        self.task_manager.set_detailed_view(checked)

    def save_settings(self):
        settings = QSettings("settings.ini", QSettings.Format.IniFormat)
        current_theme = next((key for key, action in self.theme_actions.items() if action.isChecked()), "system")
        settings.setValue("theme", current_theme)
        # POPRAWKA: Zapisujemy stan nowego przełącznika
        settings.setValue("detailed_view", self.detailed_view_action.isChecked())

    def load_settings(self):
        settings = QSettings("settings.ini", QSettings.Format.IniFormat)
        theme_name = settings.value("theme", "system", type=str)
        if theme_name in self.theme_actions:
            self.theme_actions[theme_name].setChecked(True)
            self.apply_theme(theme_name)

        # POPRAWKA: Wczytujemy stan nowego przełącznika
        detailed_view_enabled = settings.value("detailed_view", False, type=bool)
        self.detailed_view_action.setChecked(detailed_view_enabled)
        self.task_manager.set_detailed_view(detailed_view_enabled)

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        if theme_name in ["dark", "light"]:
            QApplication.setStyle(QStyleFactory.create("Fusion"))
            app.setStyleSheet(get_dark_theme_qss() if theme_name == "dark" else get_light_theme_qss())
        else:
            QApplication.setStyle(QStyleFactory.create(self.original_style_name))
            app.setStyleSheet(self.original_stylesheet)

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

    # --- Pozostałe metody bez istotnych zmian ---
    def update_eta_display(self, seconds):
        if seconds < 0: self.eta_label.setVisible(False)
        else: h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60; self.eta_label.setText(f"Czas do końca: {h:02d}:{m:02d}:{s:02d}"); self.eta_label.setVisible(True)
    def show_cancel_confirmation(self):
        selected_row = self.task_list.currentRow();
        if selected_row == -1: QMessageBox.warning(self, "Uwaga", "Najpierw zaznacz zadanie na liście."); return
        task = self.task_manager.get_task(selected_row);
        if not task: return
        is_active = selected_row == 0 and self.process_manager.is_running()
        reply = QMessageBox.question(self, "Potwierdzenie", f"Czy na pewno chcesz {'przerwać aktywne' if is_active else 'usunąć'} zadanie?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.task_manager.remove_task(selected_row)
            if is_active: self.process_manager.kill_process_and_advance()
            elif not self.process_manager.is_running(): self.process_manager.process_next_task()
    def open_component_selection_dialog(self):
        dialog = ComponentSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.batch_tasks: [self.task_manager.add_task(*task_data) for task_data in dialog.batch_tasks]
            else: self.task_manager.add_task(dialog.mkv_file, dialog.subtitle_file, dialog.font_folder, dialog.selected_script, dialog.selected_ffmpeg_script, dialog.gpu_bitrate, dialog.debug_mode, getattr(dialog, 'intro_file', None))
            if not self.process_manager.is_running(): self.process_manager.process_next_task()
    def show_diagnostic_dialog(self): dialog = DiagnosticDialog(self.output_window, self); dialog.exec()
    def show_about_dialog(self):
        platform_name = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        QMessageBox.about(self, "O programie", f"Automatyzer by kacper12gry\nVersion 4.0\n\nProgram do automatyzacji remuxowania i wypalania napisów.\n\nDziała na: {platform_name}")
    def refresh_program(self): self.close(); QProcess.startDetached(sys.executable, sys.argv)

if __name__ == "__main__":
    QGuiApplication.setDesktopFileName('pl.com.github.kacper12gry.automatyzer')
    if platform.system() == "Windows": myappid = 'com.github.kacper12gry.automatyzer'; ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    original_style_name, original_stylesheet = app.style().objectName(), app.styleSheet()
    window = MainWindow(original_style_name, original_stylesheet)
    window.show(); sys.exit(app.exec())
