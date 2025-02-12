from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QRadioButton, QButtonGroup, QSpinBox, QCheckBox, QDialogButtonBox
from pathlib import Path

class ComponentSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wybierz komponenty")
        self.setGeometry(100, 100, 600, 400)

        self.layout = QVBoxLayout()

        self.mkv_label = QLabel("Plik MKV: Nie wybrano", self)
        self.mkv_button = QPushButton("Wybierz plik MKV", self)
        self.mkv_button.clicked.connect(self.select_mkv_file)
        self.layout.addWidget(self.mkv_label)
        self.layout.addWidget(self.mkv_button)

        self.subtitle_label = QLabel("Plik z napisami: Nie wybrano", self)
        self.subtitle_button = QPushButton("Wybierz plik z napisami", self)
        self.subtitle_button.clicked.connect(self.select_subtitle_file)
        self.layout.addWidget(self.subtitle_label)
        self.layout.addWidget(self.subtitle_button)

        self.font_label = QLabel("Folder z czcionkami: Nie wybrano", self)
        self.font_button = QPushButton("Wybierz folder z czcionkami", self)
        self.font_button.clicked.connect(self.select_font_folder)
        self.layout.addWidget(self.font_label)
        self.layout.addWidget(self.font_button)

        self.ffmpeg_radio = QRadioButton("Użyj tylko FFmpeg")
        self.mkvmerge_radio = QRadioButton("Użyj tylko mkvmerge")
        self.mkvmerge_ffmpeg_radio = QRadioButton("Użyj mkvmerge i FFmpeg")
        self.mkvmerge_ffmpeg_radio.setChecked(True)

        self.button_group = QButtonGroup()
        self.button_group.addButton(self.ffmpeg_radio, 1)
        self.button_group.addButton(self.mkvmerge_ffmpeg_radio, 2)
        self.button_group.addButton(self.mkvmerge_radio, 3)

        self.layout.addWidget(self.ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_ffmpeg_radio)
        self.layout.addWidget(self.mkvmerge_radio)

        self.script1_radio = QRadioButton("CPU")
        self.script2_radio = QRadioButton("GPU (Nvidia)")
        self.script1_radio.setChecked(True)

        self.script_button_group = QButtonGroup()
        self.script_button_group.addButton(self.script1_radio, 1)
        self.script_button_group.addButton(self.script2_radio, 2)

        self.layout.addWidget(QLabel("Wybierz skrypt FFmpeg:"))
        self.layout.addWidget(self.script1_radio)
        self.layout.addWidget(self.script2_radio)

        self.bitrate_label = QLabel("GPU Bitrate (Mbps):", self)
        self.bitrate_spinbox = QSpinBox(self)
        self.bitrate_spinbox.setRange(1, 100)
        self.bitrate_spinbox.setValue(8)
        self.layout.addWidget(self.bitrate_label)
        self.layout.addWidget(self.bitrate_spinbox)

        self.debug_checkbox = QCheckBox("Debug Mode", self)
        self.layout.addWidget(self.debug_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

        self.setLayout(self.layout)

        self.mkv_file = None
        self.subtitle_file = None
        self.font_folder = None

    def select_mkv_file(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik MKV", "", "MKV Files (*.mkv);;All Files (*)", options=options
        )
        if file_path:
            self.mkv_file = Path(file_path)  # Użycie pathlib.Path
            self.mkv_label.setText(f"Plik MKV: {self.mkv_file}")

    def select_subtitle_file(self):
        options = QFileDialog.Options()
        subtitle_file, _ = QFileDialog.getOpenFileName(
            self, "Wybierz plik z napisami", "", "ASS Files (*.ass);;All Files (*)", options=options
        )
        if subtitle_file:
            self.subtitle_file = Path(subtitle_file)  # Użycie pathlib.Path
            self.subtitle_label.setText(f"Plik z napisami: {self.subtitle_file}")

    def select_font_folder(self):
        options = QFileDialog.Options()
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder z czcionkami", options=options)
        if folder_path:
            self.font_folder = Path(folder_path)  # Użycie pathlib.Path
            self.font_label.setText(f"Folder z czcionkami: {self.font_folder}")


    @property
    def selected_script(self):
        return self.button_group.checkedId()

    @property
    def selected_ffmpeg_script(self):
        return self.script_button_group.checkedId()

    @property
    def gpu_bitrate(self):
        return self.bitrate_spinbox.value()

    @property
    def debug_mode(self):
        return self.debug_checkbox.isChecked()
