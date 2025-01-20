import sys
import queue
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QListWidget, QAbstractItemView, QAction, QMessageBox, QDialog
from PyQt5.QtCore import QProcess
from PyQt5.QtGui import QIcon
from process_manager import ProcessManager
from options_dialog import OptionsDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg gui kurde by kacper12gry")
        self.setGeometry(100, 100, 600, 400)

        # Ustaw ikonę okna
        self.setWindowIcon(QIcon("icon.png"))

        self.button = QPushButton("Wybierz plik MKV", self)
        self.refresh_button = QPushButton("Odśwież", self)
        self.refresh_button.setMaximumWidth(80)
        self.refresh_button.clicked.connect(self.refresh_program)

        self.output_window = QTextEdit(self)
        self.output_window.setReadOnly(True)

        self.task_list = QListWidget(self)
        self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.cancel_button = QPushButton("Anuluj wybrane zadanie (zaznaczenie aktualnie robionego wyczyści całą liste)", self)
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

        self.queue = queue.Queue()
        self.process_manager = ProcessManager(self.queue, self.output_window, self.task_list)
        self.selected_script = 1  # Default to the first script
        self.gpu_bitrate = 8  # Default bitrate for GPU script in Mbps

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

        options_action = QAction("Options", self)
        options_action.triggered.connect(self.show_options_dialog)
        menu_bar.addAction(options_action)

        self.selected_script_label = QLabel("Selected Script: CPU", self)
        self.statusBar().addWidget(self.selected_script_label)

    def show_about_dialog(self):
        platform = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        QMessageBox.about(self, "Informacje", f"FFmpeg GUI by kacper12gry\nVersion 2.0\n\nProgram wypalający napisy na plik wideo\n\nDziała na: {platform}")

    def show_options_dialog(self):
        dialog = OptionsDialog(self, self.gpu_bitrate)
        if dialog.exec_() == QDialog.Accepted:
            self.selected_script = dialog.selected_script
            self.gpu_bitrate = dialog.gpu_bitrate
            self.update_selected_script_label()

    def update_selected_script_label(self):
        script_name = "CPU" if self.selected_script == 1 else f"GPU (Nvidia) - Bitrate: {self.gpu_bitrate}M"
        self.selected_script_label.setText(f"Selected Script: {script_name}")

    def open_file_dialog(self):
        options = QFileDialog.Options()
        mkv_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik MKV", "", "MKV Files (*.mkv);;All Files (*)", options=options)
        if mkv_file:
            subtitle_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)", options=options)
            if subtitle_file:
                font_folder = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami")
                if font_folder:
                    self.queue.put((mkv_file, subtitle_file, font_folder, self.selected_script, self.gpu_bitrate))
                    self.task_list.addItem(f"Wideo: {mkv_file}, Napisy: {subtitle_file}, Czcionki: {font_folder} (mkvmerge)")
                    if not self.process_manager.is_running():
                        self.process_manager.process_next_in_queue()

    def cancel_selected_task(self):
        selected_row = self.task_list.currentRow()
        if selected_row != -1:
            if selected_row == 0 and self.process_manager.is_running():
                self.process_manager.kill_process()
            self.task_list.takeItem(selected_row)
            # Rebuild the queue without the canceled task
            new_queue = queue.Queue()
            for i in range(self.queue.qsize()):
                task = self.queue.get()
                if i != selected_row:
                    new_queue.put(task)
            self.queue = new_queue

    def refresh_program(self):
        self.close()
        QProcess.startDetached(sys.executable, sys.argv)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
