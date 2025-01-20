from PyQt5.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QButtonGroup, QDialogButtonBox, QLabel, QHBoxLayout, QSpinBox

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
