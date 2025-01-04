import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QMenuBar, QAction, QMessageBox
from PyQt5.QtCore import QProcess

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg gui kurde by kacper12gry")
        self.setGeometry(100, 100, 600, 400)

        self.button = QPushButton("Wypalanie hardsuba", self)
        self.button.clicked.connect(self.open_file_dialog)

        self.output_window = QTextEdit(self)
        self.output_window.setReadOnly(True)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.button)
        self.layout.addWidget(self.output_window)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

        self.create_menu_bar()

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        menu_bar.addAction(about_action)

    def show_about_dialog(self):
        QMessageBox.about(self, "Informacje", "FFmpeg GUI by kacper12gry\nVersion 1.0\n\nProgram wypalający napisy na plik wideo")

    def open_file_dialog(self):
        options = QFileDialog.Options()
        mkv_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik wideo", "", "MKV Files (*.mkv);;All Files (*)", options=options)
        if mkv_file:
            subtitle_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)", options=options)
            if subtitle_file:
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
        self.process.start(" ".join(command))

    def update_output(self):
        output = self.process.readAll().data().decode()
        self.output_window.append(output)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
