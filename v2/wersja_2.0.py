import sys
import os
import queue
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QTextEdit, QVBoxLayout, QWidget, QMenuBar, QAction, QMessageBox, QListWidget, QAbstractItemView, QDialog, QRadioButton, QButtonGroup, QDialogButtonBox, QLabel, QHBoxLayout, QSpinBox, QLineEdit
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

        self.cancel_button = QPushButton("Anuluj wybrane zadanie (zaznaczenie aktualnie robionego wyczyści całą liste)", self)
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
        mkv_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik wideo", "", "MKV Files (*.mkv);;All Files (*)", options=options)
        if mkv_file:
            subtitle_file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)", options=options)
            if subtitle_file:
                self.queue.put((mkv_file, subtitle_file, self.selected_script, self.gpu_bitrate))
                self.task_list.addItem(f"Skrypt: {'CPU' if self.selected_script == 1 else f'GPU (Nvidia) - Bitrate: {self.gpu_bitrate}M'}, Wideo: {mkv_file}, Napisy: {subtitle_file}")
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
            mkv_file, subtitle_file, selected_script, gpu_bitrate = self.queue.get()
            self.process_file(mkv_file, subtitle_file, selected_script, gpu_bitrate)

    def process_file(self, mkv_file, subtitle_file, selected_script, gpu_bitrate):
        output_file = mkv_file.replace(".mkv", "_output.mp4")
        if selected_script == 1:
            command = [
                "ffmpeg", "-i", f'"{mkv_file}"', "-vf", f'format=yuv420p,subtitles="{subtitle_file}"',
                "-map_metadata", "-1", "-movflags", "faststart", "-c:v", "libx264", "-profile:v", "main",
                "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M",
                "-x264-params", "colormatrix=bt709", "-c:a", "copy", f'"{output_file}"'
            ]
        else:
            command = [
                "ffmpeg", "-y", "-vsync", "0", "-hwaccel", "cuda", "-i", f'"{mkv_file}"', "-vf", f'subtitles="{subtitle_file}"',
                "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", f'-b:v {gpu_bitrate}M', "-bufsize", "15M", "-maxrate", "15M",
                "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20",
                "-i_qfactor", "0.75", "-b_qfactor", "1.1", f'"{output_file}"'
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
        # Start the next task in the queue
        self.process_next_in_queue()

    def update_output(self):
        output = self.process.readAll().data().decode()
        self.output_window.append(output)


class OptionsDialog(QDialog):
    def __init__(self, parent=None, gpu_bitrate=8):
        super().__init__(parent)
        self.setWindowTitle("Wybierz skrypt FFmpeg")
        self.setGeometry(100, 100, 300, 200)

        self.layout = QVBoxLayout()

        self.script1_radio = QRadioButton("CPU")
        self.script2_radio = QRadioButton("GPU (Nvidia)")
        self.script1_radio.setChecked(True)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.script1_radio, 1)
        self.button_group.addButton(self.script2_radio, 2)

        self.layout.addWidget(self.script1_radio)

        gpu_layout = QHBoxLayout()
        gpu_layout.addWidget(self.script2_radio)
        self.bitrate_spinbox = QSpinBox()
        self.bitrate_spinbox.setRange(1, 100)
        self.bitrate_spinbox.setValue(gpu_bitrate)
        gpu_layout.addWidget(QLabel("Bitrate: (8 = 8000KB/s)"))
        gpu_layout.addWidget(self.bitrate_spinbox)
        self.layout.addLayout(gpu_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

        self.script2_radio.toggled.connect(self.toggle_bitrate_input)

    def toggle_bitrate_input(self):
        self.bitrate_spinbox.setDisabled(not self.script2_radio.isChecked())

    @property
    def selected_script(self):
        return self.button_group.checkedId()

    @property
    def gpu_bitrate(self):
        return self.bitrate_spinbox.value()

if __name__ == "__main__":
    # Set the QT_QPA_PLATFORM environment variable to support both Wayland and X11
    os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
