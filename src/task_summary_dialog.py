# task_summary_dialog.py

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt

class TaskSummaryDialog(QDialog):
    """Okno dialogowe wyświetlające podsumowanie zadania przed dodaniem."""
    def __init__(self, task_details, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Podsumowanie Zadania")
        self.setMinimumWidth(500)
        
        # Zastosuj styl rodzica/aplikacji
        if parent:
            self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)

        summary_label = QLabel(self._format_summary(task_details))
        summary_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Dodaj zadanie")
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Anuluj")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _format_summary(self, data):
        """Formatuje dane zadania do czytelnego formatu HTML."""
        
        # Mapowanie ID na czytelne nazwy
        script_map = {
            1: "Tylko FFmpeg (hardsub)",
            2: "Użyj mkvmerge i FFmpeg",
            3: "Tylko mkvmerge (remux)",
            4: "FFmpeg + Wstawka (intro)"
        }
        ffmpeg_script_map = {
            1: "CPU",
            2: "GPU (Nvidia CUDA)",
            3: "GPU (Intel/AMD VA-API)"
        }

        html = "<h3>Czy na pewno chcesz dodać to zadanie?</h3>"
        html += "<ul>"
        
        html += f"<li><b>Plik wideo:</b> {data.get('mkv_file').name if data.get('mkv_file') else '<i>Brak</i>'}</li>"
        
        selected_script = data.get('selected_script')
        html += f"<li><b>Główny skrypt:</b> {script_map.get(selected_script, '<i>Nieznany</i>')}</li>"

        if selected_script in [1, 2, 3]:
            html += f"<li><b>Plik napisów:</b> {data.get('subtitle_file').name if data.get('subtitle_file') else '<i>Brak</i>'}</li>"
            html += f"<li><b>Folder czcionek:</b> {data.get('font_folder').name if data.get('font_folder') else '<i>Brak</i>'}</li>"

        if selected_script == 4:
            html += f"<li><b>Plik wstawki:</b> {data.get('intro_file').name if data.get('intro_file') else '<i>Brak</i>'}</li>"

        if selected_script in [1, 2, 4]:
            ffmpeg_script = ffmpeg_script_map.get(data.get('selected_ffmpeg_script'), '<i>Nieznany</i>')
            html += f"<li><b>Enkoder FFmpeg:</b> {ffmpeg_script}</li>"
            if data.get('selected_ffmpeg_script') in [2, 3] or selected_script == 4:
                html += f"<li><b>Bitrate:</b> {data.get('gpu_bitrate')} Mbps</li>"

        if selected_script in [2, 3]:
            if data.get('subtitle_track_name'):
                 html += f"<li><b>Nazwa ścieżki napisów:</b> {data.get('subtitle_track_name')}</li>"
            if data.get('movie_name', '').strip():
                html += f"<li><b>Tytuł filmu:</b> {data.get('movie_name')}</li>"
            elif data.get('movie_name') == ' ':
                 html += "<li><b>Tytuł filmu:</b> Zachowany oryginalny</li>"
            else:
                html += "<li><b>Tytuł filmu:</b> Usunięty</li>"

        if data.get('output_path'):
            html += f"<li><b>Niestandardowy plik wyjściowy:</b> {data.get('output_path')}</li>"

        html += f"<li><b>Tryb debugowania:</b> {'Tak' if data.get('debug_mode') else 'Nie'}</li>"
        
        html += "</ul>"
        return html
