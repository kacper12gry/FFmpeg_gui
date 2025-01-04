import sys
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtCore import QProcess

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg GUI kurde")
        self.setGeometry(100, 100, 600, 400)

        self.button = QPushButton("Open File Dialog", self)
        self.button.clicked.connect(self.open_file_dialog)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.button)

        self.container = QWidget()
        self.container.setLayout(self.layout)
        self.setCentralWidget(self.container)

    def open_file_dialog(self):
        options = QFileDialog.Options()
        mkv_file, _ = QFileDialog.getOpenFileName(self, "Select MKV File", "", "MKV Files (*.mkv);;All Files (*)", options=options)
        if mkv_file:
            subtitle_file, _ = QFileDialog.getOpenFileName(self, "Select Subtitle File", "", "ASS Files (*.ass);;All Files (*)", options=options)
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

        self.output_window = QTextEdit()
        self.output_window.setReadOnly(True)
        self.layout.addWidget(self.output_window)

        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.start(" ".join(command))

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf8")
        self.output_window.append(stdout)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf8")
        self.output_window.append(stderr)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
