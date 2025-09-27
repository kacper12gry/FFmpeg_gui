# paths_config_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QWidget, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QListWidget,
                             QListWidgetItem, QDialogButtonBox, QMessageBox, QFileDialog)
from PyQt6.QtCore import QSettings

class PathsConfigDialog(QDialog):
    def __init__(self, settings: QSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Konfiguracja Ścieżek")
        self.setMinimumWidth(600)
        self.path_labels = {
            "path_1": "Folder dla 'Tylko FFmpeg'",
            "path_3": "Folder dla 'Tylko mkvmerge'",
            "path_4": "Folder dla 'FFmpeg + Wstawka'",
            "file_intro": "Domyślny plik wstawki (intro)"
        }
        self.path_edits = {}
        main_layout = QVBoxLayout(self)
        info_label = QLabel("Ustaw domyślne foldery wyjściowe oraz pliki.")
        main_layout.addWidget(info_label)
        self.list_widget = QListWidget()
        main_layout.addWidget(self.list_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Close)
        button_box.accepted.connect(self.save_paths)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        self.populate_list()

    def populate_list(self):
        for config_id, label_text in self.path_labels.items():
            saved_path = self.settings.value(config_id, "")
            item_widget = QWidget(self.list_widget)
            item_layout = QHBoxLayout(item_widget)
            label = QLabel(label_text)
            path_edit = QLineEdit(saved_path)
            browse_button = QPushButton("...")
            if config_id.startswith("file_"):
                path_edit.setPlaceholderText("Brak domyślnego pliku")
                browse_button.setText("Wybierz plik...")
                browse_button.clicked.connect(lambda checked, edit=path_edit: self.select_file(edit))
            else:
                path_edit.setPlaceholderText("Brak domyślnego folderu")
                browse_button.setText("Przeglądaj...")
                browse_button.clicked.connect(lambda checked, edit=path_edit: self.select_directory(edit))
            item_layout.addWidget(label); item_layout.addWidget(path_edit); item_layout.addWidget(browse_button)
            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, item_widget)
            self.path_edits[config_id] = path_edit

    def select_directory(self, path_edit: QLineEdit):
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder", path_edit.text())
        if directory: path_edit.setText(directory)

    def select_file(self, path_edit: QLineEdit):
        file, _ = QFileDialog.getOpenFileName(self, "Wybierz plik", path_edit.text(), "Pliki wideo (*.mp4 *.mkv)")
        if file: path_edit.setText(file)

    def save_paths(self):
        for config_id, path_edit in self.path_edits.items():
            self.settings.setValue(config_id, path_edit.text())
        QMessageBox.information(self, "Zapisano", "Konfiguracja ścieżek została zapisana.")
        self.accept()
