from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QDialogButtonBox, QLineEdit, QPushButton, 
    QFileDialog, QComboBox, QSpinBox, QCheckBox, QWidget, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from pathlib import Path
from dataclasses import make_dataclass, astuple

# Zaktualizowana struktura danych, zawiera teraz listę ostrzeżeń
TaskData = make_dataclass("TaskData", ["mkv", "sub", "font", "script", "ffmpeg", "bitrate", "debug", "intro", "output", "warnings", "audio"])

class BatchEditDialog(QDialog):
    def __init__(self, tasks_data, parent=None, batch_import_logic=None):
        super().__init__(parent)
        self.setWindowTitle("Podsumowanie i Edycja Importowanych Zadań")
        self.setMinimumSize(1000, 600)

        # Mapuj dane wejściowe na TaskData (obsługa starego formatu bez audio)
        self.tasks = []
        for task in tasks_data:
            if len(task) < 11:
                # Jeśli brakuje pola audio (np. stary import), dodaj None (czyli domyślne ID 1)
                self.tasks.append(TaskData(*(list(task) + [None])))
            else:
                self.tasks.append(TaskData(*task))

        self.batch_import_logic = batch_import_logic

        self._setup_ui()

        self.task_list.currentItemChanged.connect(self._display_task_details)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.script_combo.currentIndexChanged.connect(self._update_form_state)
        self.encoder_combo.currentIndexChanged.connect(self._update_form_state)
        self.import_more_button.clicked.connect(self._import_more_tasks)
        self.up_button.clicked.connect(self._move_task_up)
        self.down_button.clicked.connect(self._move_task_down)
        self.delete_button.clicked.connect(self._delete_task)

        self._populate_list()
        if self.task_list.count() > 0:
            self.task_list.setCurrentRow(0)

    def _import_more_tasks(self):
        if not self.batch_import_logic:
            QMessageBox.critical(self, "Błąd", "Wystąpił błąd wewnętrzny: Brak dostępu do logiki importu.")
            return
        
        new_tasks_data = self.batch_import_logic.get_tasks_from_file()
        if new_tasks_data:
            current_item = self.task_list.currentItem()
            if current_item:
                self._save_current_task_details(current_item)

            new_tasks = [TaskData(*task) for task in new_tasks_data]
            self.tasks.extend(new_tasks)
            self._populate_list()
            self.task_list.setCurrentRow(len(self.tasks) - len(new_tasks))

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Kontener dla listy i przycisków
        list_container = QWidget()
        list_layout = QHBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self.task_list = QListWidget()
        list_layout.addWidget(self.task_list)

        # Przyciski do zarządzania listą
        button_panel = QVBoxLayout()
        button_panel.setSpacing(5)
        self.up_button = QPushButton(QIcon.fromTheme("go-up"), "")
        self.down_button = QPushButton(QIcon.fromTheme("go-down"), "")
        self.delete_button = QPushButton(QIcon.fromTheme("edit-delete"), "")
        self.up_button.setToolTip("Przesuń zaznaczone zadanie w górę")
        self.down_button.setToolTip("Przesuń zaznaczone zadanie w dół")
        self.delete_button.setToolTip("Usuń zaznaczone zadanie")
        
        button_panel.addWidget(self.up_button)
        button_panel.addWidget(self.down_button)
        button_panel.addStretch()
        button_panel.addWidget(self.delete_button)
        list_layout.addLayout(button_panel)

        splitter.addWidget(list_container)

        form_widget = QWidget()
        self.form_layout = QFormLayout(form_widget)
        self.form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        splitter.addWidget(form_widget)

        self.mkv_edit = self._create_path_widget(is_file=True, file_filter="MKV Files (*.mkv)")
        self.sub_edit = self._create_path_widget(is_file=True, file_filter="ASS Files (*.ass)")
        self.font_edit = self._create_path_widget(is_file=False)
        self.intro_edit = self._create_path_widget(is_file=True, file_filter="Video Files (*.mp4 *.mkv)")
        self.audio_spin = QSpinBox()
        self.audio_spin.setRange(0, 99)
        self.script_combo = self._create_script_combo()
        self.encoder_combo = self._create_encoder_combo()
        self.bitrate_spin = self._create_bitrate_spinbox()
        self.debug_check = self._create_debug_checkbox()

        self.form_layout.addRow("Plik MKV:", self.mkv_edit)
        self.form_layout.addRow("Napisy:", self.sub_edit)
        self.form_layout.addRow("Czcionki:", self.font_edit)
        self.form_layout.addRow("Wstawka:", self.intro_edit)
        self.form_layout.addRow("Audio ID:", self.audio_spin)
        self.form_layout.addRow("Skrypt:", self.script_combo)
        self.form_layout.addRow("Enkoder:", self.encoder_combo)
        self.form_layout.addRow("Bitrate:", self.bitrate_spin)
        self.form_layout.addRow("Debug:", self.debug_check)
        
        self.form_widget = form_widget
        self.form_widget.setEnabled(False)

        splitter.setSizes([300, 700])

        bottom_buttons_layout = QHBoxLayout()
        self.import_more_button = QPushButton("Importuj więcej...")
        bottom_buttons_layout.addWidget(self.import_more_button)
        bottom_buttons_layout.addStretch()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Zatwierdź i dodaj zadania")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj import")
        bottom_buttons_layout.addWidget(self.button_box)
        
        main_layout.addLayout(bottom_buttons_layout)

    def _populate_list(self):
        self.task_list.clear()
        for i, task in enumerate(self.tasks):
            text = f"Zadanie {i+1}: {task.mkv.name if task.mkv else 'Nowe zadanie'}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, task) # Przechowuj cały obiekt zadania
            
            if task.warnings:
                item.setIcon(QIcon.fromTheme("dialog-warning"))
                item.setToolTip("\n".join(task.warnings))

            self.task_list.addItem(item)

    def _display_task_details(self, current, previous):
        if previous:
            self._save_current_task_details(previous)

        if not current:
            self.form_widget.setEnabled(False)
            return

        self.form_widget.setEnabled(True)
        task = current.data(Qt.ItemDataRole.UserRole) # Pobierz obiekt zadania

        for child in self.form_widget.findChildren(QWidget):
            child.blockSignals(True)

        self.mkv_edit.findChild(QLineEdit).setText(str(task.mkv) if task.mkv else "")
        self.sub_edit.findChild(QLineEdit).setText(str(task.sub) if task.sub else "")
        self.font_edit.findChild(QLineEdit).setText(str(task.font) if task.font else "")
        self.intro_edit.findChild(QLineEdit).setText(str(task.intro) if task.intro else "")
        self.audio_spin.setValue(task.audio if task.audio is not None else 1)
        self.script_combo.setCurrentIndex(task.script - 1 if 1 <= task.script <= 4 else 2)
        self.encoder_combo.setCurrentIndex(task.ffmpeg - 1 if 1 <= task.ffmpeg <= 4 else 0)
        self.bitrate_spin.setValue(task.bitrate)
        self.debug_check.setChecked(task.debug)

        for child in self.form_widget.findChildren(QWidget):
            child.blockSignals(False)
        
        self._update_form_state()

    def _save_current_task_details(self, item):
        if not item:
            return
        
        task_to_update = item.data(Qt.ItemDataRole.UserRole)
        try:
            task_index = self.tasks.index(task_to_update)
        except ValueError:
            # To nie powinno się zdarzyć, ale zabezpieczamy
            return

        mkv_path = self.mkv_edit.findChild(QLineEdit).text()
        sub_path = self.sub_edit.findChild(QLineEdit).text()
        font_path = self.font_edit.findChild(QLineEdit).text()
        intro_path = self.intro_edit.findChild(QLineEdit).text()
        
        # Stwórz nowy, zaktualizowany obiekt i podmień go na liście
        updated_task = TaskData(
            mkv=Path(mkv_path) if mkv_path else None,
            sub=Path(sub_path) if sub_path else None,
            font=Path(font_path) if font_path else None,
            script=self.script_combo.currentIndex() + 1,
            ffmpeg=self.encoder_combo.currentIndex() + 1,
            bitrate=self.bitrate_spin.value(),
            debug=self.debug_check.isChecked(),
            intro=Path(intro_path) if intro_path else None,
            output=task_to_update.output, # Zachowaj oryginalne wartości
            warnings=task_to_update.warnings,
            audio=self.audio_spin.value()
        )
        self.tasks[task_index] = updated_task
        
        # Zaktualizuj także dane w samym itemie listy
        item.setData(Qt.ItemDataRole.UserRole, updated_task)
        item.setText(f"Zadanie {task_index+1}: {updated_task.mkv.name if updated_task.mkv else 'Nowe zadanie'}")

    def get_edited_tasks(self):
        self._save_current_task_details(self.task_list.currentItem())
        return [astuple(task) for task in self.tasks]

    def _delete_task(self):
        current_row = self.task_list.currentRow()
        if current_row == -1:
            return
        
        reply = QMessageBox.question(self, "Potwierdzenie", 
                                     "Czy na pewno chcesz usunąć to zadanie z listy?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return

        del self.tasks[current_row]
        self._populate_list()

        # Ustaw zaznaczenie na elemencie, który zajął miejsce usuniętego
        if self.tasks:
            new_row = min(current_row, len(self.tasks) - 1)
            self.task_list.setCurrentRow(new_row)

    def _move_task_up(self):
        current_row = self.task_list.currentRow()
        if current_row <= 0:
            return
        
        # Zapisz bieżące zmiany przed przesunięciem
        self._save_current_task_details(self.task_list.currentItem())

        self.tasks[current_row], self.tasks[current_row - 1] = self.tasks[current_row - 1], self.tasks[current_row]
        self._populate_list()
        self.task_list.setCurrentRow(current_row - 1)

    def _move_task_down(self):
        current_row = self.task_list.currentRow()
        if current_row == -1 or current_row >= len(self.tasks) - 1:
            return

        # Zapisz bieżące zmiany przed przesunięciem
        self._save_current_task_details(self.task_list.currentItem())

        self.tasks[current_row], self.tasks[current_row + 1] = self.tasks[current_row + 1], self.tasks[current_row]
        self._populate_list()
        self.task_list.setCurrentRow(current_row + 1)

    def _update_form_state(self):
        script_type = self.script_combo.currentIndex() + 1
        encoder_type = self.encoder_combo.currentIndex() + 1

        needs_subtitles = script_type in [1, 2, 3]
        needs_intro = script_type == 4
        needs_ffmpeg = script_type in [1, 2, 4]
        needs_bitrate = (needs_ffmpeg and encoder_type in [2, 3]) or script_type == 4

        self.sub_edit.setEnabled(needs_subtitles)
        self.font_edit.setEnabled(needs_subtitles)
        self.intro_edit.setEnabled(needs_intro)
        self.encoder_combo.setEnabled(needs_ffmpeg)
        self.bitrate_spin.setEnabled(needs_bitrate)

    def _create_path_widget(self, is_file=True, file_filter="All Files (*)"):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        line_edit = QLineEdit()
        button = QPushButton("...")
        button.setFixedWidth(30)
        layout.addWidget(line_edit)
        layout.addWidget(button)

        def browse():
            current_path = line_edit.text()
            try:
                if Path(current_path).is_dir():
                    start_dir = current_path
                else:
                    start_dir = str(Path(current_path).parent)
            except Exception:
                start_dir = ""

            if is_file:
                new_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik", start_dir, file_filter)
            else:
                new_path = QFileDialog.getExistingDirectory(self, "Wybierz folder", start_dir)
            if new_path:
                line_edit.setText(new_path)
        
        button.clicked.connect(browse)
        return widget

    def _create_script_combo(self):
        combo = QComboBox()
        combo.addItems(["1: Hardsub", "2: Remux+Hardsub", "3: Remux", "4: Wstawka"])
        return combo

    def _create_encoder_combo(self):
        combo = QComboBox()
        combo.addItems(["1: CPU (CRF)", "2: GPU (Nvidia CUDA)", "3: GPU (Intel/AMD VA-API)", "4: GPU (Intel/AMD VA-API AV1)"])
        return combo

    def _create_bitrate_spinbox(self):
        spin = QSpinBox()
        spin.setRange(0, 100)
        return spin

    def _create_debug_checkbox(self):
        return QCheckBox()
