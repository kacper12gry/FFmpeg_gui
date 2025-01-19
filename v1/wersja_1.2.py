import sys
import os
import queue
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QMenuBar, QAction, QMessageBox, QListWidget, QAbstractItemView
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QProcess

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg gui kurde by kacper12gry")
        self.setGeometry(100, 100, 600, 400)

        # Ustaw ikonę okna
        self.setWindowIcon(QIcon("icon.png"))

        self.button = QPushButton("Wypalanie hardsuba", self)
        self.button.clicked.connect(self.open_file_dialog)

        self.output_window = QTextEdit(self)
        self.output_window.setReadOnly(True)

        self.task_list = QListWidget(self)
        self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)

        self.cancel_button = QPushButton("Anuluj wybrane zadanie", self)
        self.cancel_button.clicked.connect(self.cancel_selected_task)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.task_list)
        self.layout.addWidget(self.cancel_button)
        self.layout.addWidget(self.output_window)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        self.create_menu_bar()

        self.queue = queue.Queue()
        self.process = None

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    def show_about_dialog(self):
        platform = "Wayland" if "wayland" in os.getenv("XDG_SESSION_TYPE", "").lower() else "X11"
        QMessageBox.about(self, "Informacje", f"FFmpeg GUI by kacper12gry\nVersion 1.1\n\nProgram wypalający napisy na plik wideo\n\nDziała na: {platform}")

    def open_file_dialog(self):
        options = QFileDialog.Options()
        mkv_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik wideo", "", "MKV Files (*.mkv);;All Files (*)", options=options)
        if mkv_file:
            subtitle_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)", options=options)
            if subtitle_file:
                self.queue.put((mkv_file, subtitle_file))
                self.task_list.addItem(f"Wideo: {mkv_file}, Napisy: {subtitle_file}")
                if not self.process or self.process.state() == QProcess.NotRunning:
                    self.process_next_in_queue()

    def cancel_selected_task(self):
        selected_row = self.task_list.currentRow()
        if selected_row != -1:
            if selected_row == 0 and self.process and self.process.state() == QProcess.Running:
                self.process.kill()
            self.task_list.takeItem(selected_row)
            # Rebuild the queue without the canceled task
            new_queue = queue.Queue()
            for i in range(self.queue.qsize()):
                task = self.queue.get()
                if i != selected_row:
                    new_queue.put(task)
            self.queue = new_queue

    def process_next_in_queue(self):
        if not self.queue.empty():
            mkv_file, subtitle_file = self.queue.get()
            self.process_file(mkv_file, subtitle_file)

    def process_file(self, mkv_file, subtitle_file):
        output_file = mkv_file.replace(".mkv", "_output.mp4")
        command = [
            "ffmpeg", "-i", f'"{mkv_file}"', "-vf", f'format=yuv420p,subtitles="{subtitle_file}"',
            "-map_metadata", "-1", "-movflags", "faststart", "-c:v", "libx264", "-profile:v", "main",
            "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M",
            "-x264-params", "colormatrix=bt709", "-c:a", "copy", f'"{output_file}"'
        ]

        self.output_window.clear()  # Clear the output window before starting a new process

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(self.process_next_in_queue)
        self.process.finished.connect(self.mark_task_as_done)
        self.process.start(" ".join(command))

        # Zaznacz aktualnie wykonywane zadanie
        self.task_list.setCurrentRow(0)

    def mark_task_as_done(self):
        # Usuń ukończone zadanie z listy
        self.task_list.takeItem(0)

    def update_output(self):
        output = self.process.readAll().data().decode()
        self.output_window.append(output)

if __name__ == "__main__":
    # Set the QT_QPA_PLATFORM environment variable to support both Wayland and X11
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
