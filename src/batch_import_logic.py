# batch_import_logic.py

from pathlib import Path
from PyQt6.QtWidgets import QFileDialog, QMessageBox, QDialog
from batch_edit_dialog import BatchEditDialog # NOWY IMPORT

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
            <li>Typ enkodera FFmpeg (1=CPU, 2=GPU CUDA, 3=GPU VA-API)</li>
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

    def _parse_txt_lines(self, lines):
        tasks_to_process, fatal_errors = [], []
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

            warnings = []
            mkv_path = Path(mkv_path_str) if mkv_path_str else None
            subtitle_path = Path(sub_path_str) if sub_path_str else None
            font_folder = Path(font_path_str) if font_path_str else None
            intro_path = Path(intro_path_str) if intro_path_str else None

            if not mkv_path:
                warnings.append("Brak ścieżki do pliku MKV.")
            elif not mkv_path.is_file():
                warnings.append(f"Plik MKV nie istnieje: {mkv_path_str}")

            if script_type in [1, 2, 3]:
                if not subtitle_path:
                    warnings.append("Brak ścieżki do napisów.")
                elif not subtitle_path.is_file():
                    warnings.append(f"Plik napisów nie istnieje: {sub_path_str}")
                if not font_folder:
                    warnings.append("Brak folderu czcionek.")
                elif not font_folder.is_dir():
                    warnings.append(f"Folder czcionek nie istnieje: {font_path_str}")
            
            if script_type == 4:
                if not intro_path:
                    warnings.append("Brak ścieżki do wstawki.")
                elif not intro_path.is_file():
                    warnings.append(f"Plik wstawki nie istnieje: {intro_path_str}")

            if script_type not in [1, 2, 3, 4]:
                warnings.append(f"Nieznany typ skryptu: {script_type}. Ustawiono domyślny (3).")
                script_type = 3

            if script_type == 3:
                ffmpeg_type = 0
                bitrate = 0

            task_data = (mkv_path, subtitle_path, font_folder, script_type, ffmpeg_type, bitrate, debug, intro_path, None, warnings)
            tasks_to_process.append(task_data)
        
        return tasks_to_process, fatal_errors

    def get_tasks_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self.parent, "Wybierz plik z zadaniami", "", "Text Files (*.txt);;All Files (*)")
        if not file_path:
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            QMessageBox.critical(self.parent, "Błąd", f"Nie udało się otworzyć pliku: {e}")
            return None

        tasks_to_process, fatal_errors = self._parse_txt_lines(lines)

        if fatal_errors:
            QMessageBox.critical(self.parent, "Błędy krytyczne", "Wystąpiły krytyczne błędy uniemożliwiające import:\n\n" + "\n".join(fatal_errors))
            return None

        if not tasks_to_process:
            QMessageBox.information(self.parent, "Informacja", "Nie znaleziono zadań do zaimportowania w pliku.")
            return None
        
        return tasks_to_process

    def import_from_txt(self):
        tasks_to_process = self.get_tasks_from_file()
        if tasks_to_process is None:
            return None

        edit_dialog = BatchEditDialog(tasks_to_process, self.parent, self)
        if edit_dialog.exec() == QDialog.DialogCode.Accepted:
            final_tasks = edit_dialog.get_edited_tasks()
            if final_tasks:
                final_tasks_cleaned = [task[:-1] for task in final_tasks]
                return final_tasks_cleaned
        
        return None # Zwróć None, jeśli anulowano