import sys
import queue
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QListWidget, QAbstractItemView, QAction, QMessageBox, QDialogButtonBox, QDialog
from PyQt5.QtCore import QProcess
from PyQt5.QtGui import QIcon
from process_manager import ProcessManager
from component_selection_dialog import ComponentSelectionDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg gui kurde by kacper12gry")
        self.setGeometry(100, 100, 600, 400)

        # Ustaw ikonę okna
        self.setWindowIcon(QIcon("icon.png"))

        self.button = QPushButton("Otwórz okno wyboru komponentów", self)
        self.button.clicked.connect(self.open_component_selection_dialog)

        self.refresh_button = QPushButton("Odśwież", self)
        self.refresh_button.setMaximumWidth(100)
        self.refresh_button.clicked.connect(self.refresh_program)

        self.output_window = QTextEdit(self)
        self.output_window.setReadOnly(True)

        self.task_list = QListWidget(self)
        self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)

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

        self.queue = queue.Queue()
        self.selected_script = 1  # Default to the first script
        self.gpu_bitrate = 8  # Default bitrate for GPU script in Mbps
        self.debug_mode = False
        self.process_manager = ProcessManager(self.queue, self.output_window, self.task_list, debug_mode=self.debug_mode, selected_script=self.selected_script, gpu_bitrate=self.gpu_bitrate)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    def show_about_dialog(self):
        platform = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        QMessageBox.about(self, "Informacje", f"FFmpeg GUI by kacper12gry\nVersion 2.2\n\nProgram automatyzer remuxowania i wypalania napisów\n\nDziała na: {platform}")

    def open_component_selection_dialog(self):
        dialog = ComponentSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            mkv_file = dialog.mkv_file
            subtitle_file = dialog.subtitle_file
            font_folder = dialog.font_folder
            selected_script = dialog.selected_script
            selected_ffmpeg_script = dialog.selected_ffmpeg_script
            gpu_bitrate = dialog.gpu_bitrate
            debug_mode = dialog.debug_mode
            self.queue.put((mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode))
            task_description = f"Wideo: {mkv_file}, Napisy: {subtitle_file}, Czcionki: {font_folder}, FFmpeg: {selected_ffmpeg_script} ({'mkvmerge' if selected_script == 2 else 'ffmpeg'})"
            self.task_list.addItem(task_description)
            if not self.process_manager.is_running():
                self.process_manager.process_next_in_queue()

        # Upewnij się, że okno jest aktywowane po otwarciu dialogu
        self.raise_()  # Podnosi okno na wierzch
        self.activateWindow()  # Aktywuje okno

    def cancel_selected_task(self):
        selected_row = self.task_list.currentRow()
        if selected_row == -1:
            return  # Nie wybrano żadnego zadania

        tasks = list(self.queue.queue)  # Pobieramy listę z kolejki

        # Sprawdzamy, czy wybrany wiersz to aktualnie przetwarzane zadanie
        if selected_row == 0 and self.process_manager.is_running():
            self.process_manager.kill_process()  # Zatrzymujemy proces

        # Usuwamy zadanie z listy i kolejki
        self.task_list.takeItem(selected_row)
        tasks.pop(selected_row)

        # Odtwarzamy kolejkę bez usuniętego zadania
        self.queue = queue.Queue()
        for task in tasks:
            self.queue.put(task)

        # Jeśli anulowano aktualnie wykonywane zadanie, uruchamiamy następne
        if selected_row == 0:
            self.process_manager.process_next_in_queue()

    def kill_process(self):
        if self.process:
            self.process.kill()
            self.process.waitForFinished()
            self.process.close()
            self.process = None  # Upewniamy się, że proces jest usunięty

    def refresh_program(self):
        self.close()
        QProcess.startDetached(sys.executable, sys.argv)

        # Upewnij się, że okno zostanie ponownie aktywowane po odświeżeniu
        self.raise_()  # Podnosi okno na wierzch
        self.activateWindow()  # Aktywuje okno

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
