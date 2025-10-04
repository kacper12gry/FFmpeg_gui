# batch_import_logic.py

from pathlib import Path
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, QDialogButtonBox
from PyQt6.QtCore import Qt

class BatchImportLogic:
    def __init__(self, parent_dialog):
        self.parent = parent_dialog

    def show_import_help_dialog(self):
        help_text = """
        <h4>Format pliku TXT do importu zadań</h4>
        <p>Plik powinien zawierać jedno zadanie w każdej linii. Pola w linii muszą być oddzielone średnikiem (<b>;</b>).</p>
        <p><b>Wymagane jest 8 pól w następującej kolejności:</b></p>
        <ol>
            <li>Pełna ścieżka do pliku wideo (MKV)</li>
            <li>Pełna ścieżka do pliku napisów (.ass)</li>
            <li>Pełna ścieżka do folderu z czcionkami</li>
            <li>Typ skryptu (1, 2, 3 lub 4)</li>
            <li>Typ enkodera FFmpeg (1=CPU, 2=GPU)</li>
            <li>Bitrate (np. 8, 12)</li>
            <li>Tryb debugowania (true lub false)</li>
            <li>Pełna ścieżka do pliku wstawki (intro)</li>
        </ol>
        <p><b>Ważne:</b></p>
        <ul>
            <li>Jeśli któreś pole nie jest używane, zostaw je puste, ale zachowaj średniki (np. <code>...;;;...</code>).</li>
            <li>Linie zaczynające się od <b>#</b> są ignorowane.</li>
        </ul>
        """
        QMessageBox.information(self.parent, "Pomoc - Format pliku TXT", help_text)

    def import_from_txt(self):
        file_path, _ = QFileDialog.getOpenFileName(self.parent, "Wybierz plik z zadaniami", "", "Text Files (*.txt);;All Files (*)")
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self.parent, "Błąd", f"Nie udało się otworzyć pliku: {e}")
            return

        valid_tasks, ignorable_warnings, fatal_errors = [], [], []
        for i, line in enumerate(lines):
            line_num, line_content = i + 1, line.strip()
            if not line_content or line_content.startswith('#'):
                continue
            parts = [p.strip() for p in line_content.split(';')]
            while len(parts) < 8:
                parts.append("")
            if len(parts) > 8:
                fatal_errors.append(f"Linia {line_num}: Zbyt wiele pól (oczekiwano 8, otrzymano {len(parts)}).")
                continue
            mkv_path_str, sub_path_str, font_path_str, script_str, ffmpeg_str, bitrate_str, debug_str, intro_path_str = parts
            try:
                script_type = int(script_str) if script_str else 0
                ffmpeg_type = int(ffmpeg_str) if ffmpeg_str else 0
                bitrate = int(bitrate_str) if bitrate_str else 0
                debug = debug_str.lower() in ['true', '1', 'tak']
            except ValueError:
                fatal_errors.append(f"Linia {line_num}: Błędny format danych (liczby).")
                continue
            line_errors = []
            if script_type in [1, 2] and ffmpeg_type not in [1, 2]:
                line_errors.append("Brak typu enkodera (1=CPU, 2=GPU).")
            if (script_type in [1, 2] and ffmpeg_type == 2 and bitrate <= 0):
                line_errors.append("Brak bitrate dla GPU.")
            if (script_type == 4 and bitrate <= 0):
                line_errors.append("Brak bitrate dla skryptu 4.")
            if script_type not in [1, 2, 3, 4]:
                 line_errors.append(f"Nieznany typ skryptu: {script_type}.")
            if not mkv_path_str:
                line_errors.append("Brak ścieżki do pliku MKV.")

            if line_errors:
                fatal_errors.append(f"Linia {line_num}: " + ", ".join(line_errors))
                continue

            mkv_path = Path(mkv_path_str) if mkv_path_str else None
            subtitle_path = Path(sub_path_str) if sub_path_str else None
            font_folder = Path(font_path_str) if font_path_str else None
            intro_path = Path(intro_path_str) if intro_path_str else None

            line_warnings = []
            if mkv_path and not mkv_path.is_file():
                line_warnings.append(f"Plik MKV nie istnieje: '{mkv_path_str}'")
            if script_type in [1, 2, 3] and subtitle_path and not subtitle_path.is_file():
                line_warnings.append(f"Plik napisów nie istnieje: '{sub_path_str}'")
            if script_type in [1, 2, 3] and font_folder and not font_folder.is_dir():
                line_warnings.append(f"Folder czcionek nie istnieje: '{font_path_str}'")
            if script_type == 4 and intro_path and not intro_path.is_file():
                line_warnings.append(f"Plik wstawki nie istnieje: '{intro_path_str}'")

            task_data = (mkv_path, subtitle_path, font_folder, script_type, ffmpeg_type, bitrate, debug, intro_path, None)
            if not line_warnings:
                valid_tasks.append(task_data)
            else:
                ignorable_warnings.append((f"Linia {line_num}: " + ", ".join(line_warnings), task_data))

        if fatal_errors:
            QMessageBox.critical(self.parent, "Błędy krytyczne", "Wystąpiły krytyczne błędy importu:\n\n" + "\n".join(fatal_errors))
            return

        if ignorable_warnings:
            error_dialog = ErrorSelectionDialog(ignorable_warnings, self.parent)
            if error_dialog.exec() == QDialog.DialogCode.Accepted:
                valid_tasks.extend(error_dialog.get_selected_tasks())

        if valid_tasks:
            self.parent.batch_tasks = valid_tasks
            QMessageBox.information(self.parent, "Sukces", f"Pomyślnie zaimportowano {len(valid_tasks)} zadań.")
            self.parent.accept()
        elif not fatal_errors and not ignorable_warnings:
            QMessageBox.information(self.parent, "Informacja", "Nie znaleziono zadań do zaimportowania w pliku.")


class ErrorSelectionDialog(QDialog):
    def __init__(self, warnings_data, parent=None):
        super().__init__(parent)
        self.setStyleSheet(QApplication.instance().styleSheet())
        self.setWindowTitle("Wykryto problemy - wybierz zadania do dodania")
        self.setMinimumWidth(700)
        self.warnings_data = warnings_data
        layout = QVBoxLayout(self)
        info_label = QLabel("Wykryto potencjalne problemy w poniższych zadaniach.\nZaznacz te, które chcesz mimo wszystko dodać do kolejki.", self)
        layout.addWidget(info_label)
        self.list_widget = QListWidget(self)
        for text, task_data in self.warnings_data:
            item = QListWidgetItem(text, self.list_widget)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, task_data)
        layout.addWidget(self.list_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_selected_tasks(self):
        selected_tasks = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_tasks.append(item.data(Qt.ItemDataRole.UserRole))
        return selected_tasks
