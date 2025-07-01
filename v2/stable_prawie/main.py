# main.py
import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout,
                             QHBoxLayout, QWidget, QLabel, QListWidget, QAbstractItemView,
                             QMessageBox, QDialog)
from PyQt6.QtCore import QProcess
from PyQt6.QtGui import QIcon, QAction
from process_manager import ProcessManager
from component_selection_dialog import ComponentSelectionDialog
from pathlib import Path
from task_manager import TaskManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Automatyzer kurde by kacper12gry")
        self.setGeometry(100, 100, 600, 400)

        self.setWindowIcon(QIcon("icon.png"))

        self.button = QPushButton("Otwórz okno wyboru komponentów", self)
        self.button.clicked.connect(self.open_component_selection_dialog)

        self.refresh_button = QPushButton("Odśwież", self)
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.clicked.connect(self.refresh_program)

        self.output_window = QTextEdit(self)
        self.output_window.setReadOnly(True)

        self.task_list = QListWidget(self)
        self.task_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.cancel_button = QPushButton("Anuluj wybrane zadanie", self)
        self.cancel_button.clicked.connect(self.cancel_selected_task)

        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.button)
        self.button_layout.addWidget(self.refresh_button)

        self.layout = QVBoxLayout()
        self.layout.addLayout(self.button_layout)
        self.layout.addWidget(self.task_list)
        self.layout.addWidget(self.cancel_button)
        self.layout.addWidget(self.output_window)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        self.create_menu_bar()

        self.task_manager = TaskManager(self.task_list)
        self.process_manager = ProcessManager(self.task_manager, self.output_window, debug_mode=False)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    def show_about_dialog(self):
        platform = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        QMessageBox.about(self, "Informacje", f"Automatyzer by kacper12gry\nVersion 3.0\n\nProgram automatyzer remuxowania i wypalania napisów\n\nDziała na: {platform}")

    def open_component_selection_dialog(self):
        dialog = ComponentSelectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.batch_tasks:
                for task in dialog.batch_tasks:
                    mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode, intro_file = task
                    self.task_manager.add_task(mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode, intro_file)
            else:
                self.task_manager.add_task(dialog.mkv_file, dialog.subtitle_file, dialog.font_folder, dialog.selected_script, dialog.selected_ffmpeg_script, dialog.gpu_bitrate, dialog.debug_mode, getattr(dialog, 'intro_file', None))

            if not self.process_manager.is_running():
                self.process_manager.process_next_task()

        self.raise_()
        self.activateWindow()

    def cancel_selected_task(self):
        selected_row = self.task_list.currentRow()
        if selected_row == -1: return

        if selected_row == 0 and self.process_manager.is_running():
            self.process_manager.kill_process()

        self.task_manager.remove_task(selected_row)

        if selected_row == 0 and self.task_manager.has_tasks() and not self.process_manager.is_running():
            self.process_manager.process_next_task()

    def refresh_program(self):
        self.close()
        QProcess.startDetached(sys.executable, sys.argv)
        self.raise_()
        self.activateWindow()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
