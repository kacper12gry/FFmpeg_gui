# task_manager.py
from PyQt6.QtWidgets import QListWidget, QListWidgetItem
from PyQt6.QtGui import QColor
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Task:
    mkv_file: Path
    subtitle_file: Path | None
    font_folder: Path | None
    selected_script: int
    selected_ffmpeg_script: int
    gpu_bitrate: int
    debug_mode: bool
    intro_file: Path | None
    status: str = "Oczekuje"

    def get_description(self, detailed: bool = False):
        """
        POPRAWKA: Ostateczna wersja, która zawsze stawia nazwę pliku na czele
        i ma spójną strukturę, a 'detailed' kontroluje tylko format ścieżek.
        """
        def path_repr(path_obj: Path | None) -> str:
            if not path_obj: return "Brak"
            return str(path_obj) if detailed else path_obj.name

        # Zawsze zaczynamy od nazwy pliku
        base_description = self.mkv_file.name
        details = []

        # Dodajemy szczegóły w zależności od typu skryptu
        if self.selected_script == 1:
            encoder = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU ({self.gpu_bitrate} Mbps)"
            details.append(f"Typ: Hardsub | Enkoder: {encoder}")
        elif self.selected_script == 2:
            encoder = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU ({self.gpu_bitrate} Mbps)"
            details.append(f"Typ: Remux + Hardsub | Enkoder: {encoder}")
            details.append(f"Napisy: {path_repr(self.subtitle_file)} | Czcionki: {path_repr(self.font_folder)}")
        elif self.selected_script == 3:
            details.append("Typ: Tylko Remux")
            details.append(f"Napisy: {path_repr(self.subtitle_file)} | Czcionki: {path_repr(self.font_folder)}")
        elif self.selected_script == 4:
            details.append(f"Typ: FFmpeg + Wstawka | Bitrate: {self.gpu_bitrate} Mbps")
            details.append(f"Wstawka: {path_repr(self.intro_file)}")

        if self.status != "Oczekuje":
            details.append(f"Status: {self.status}")

        return f"{base_description} | {' | '.join(details)}"

class TaskManager:
    def __init__(self, task_list_widget: QListWidget, process_manager):
        self.tasks = []
        self.task_list_widget = task_list_widget
        self.process_manager = process_manager
        self.detailed_view = False

    def update_list_widget(self):
        self.task_list_widget.clear()
        is_processing = self.process_manager.is_running()

        for i, task in enumerate(self.tasks):
            description = task.get_description(detailed=self.detailed_view)

            if i == 0 and is_processing:
                description = "► " + description

            item = QListWidgetItem(description)

            if "Przetwarzanie" in task.status or "Przygotowywanie" in task.status or "Krok" in task.status:
                item.setForeground(QColor("#E67E22"))
            elif "Błąd" in task.status:
                item.setForeground(QColor("#F44336"))

            self.task_list_widget.addItem(item)

    # --- Pozostałe metody bez zmian ---
    def set_detailed_view(self, enabled: bool): self.detailed_view = enabled; self.update_list_widget()
    def add_task(self, *args, **kwargs): task = Task(*args, **kwargs); self.tasks.append(task); self.update_list_widget()
    def remove_task(self, index: int):
        if 0 <= index < len(self.tasks): self.tasks.pop(index); self.update_list_widget()
    def get_task(self, index: int): return self.tasks[index] if 0 <= index < len(self.tasks) else None
    def has_tasks(self): return len(self.tasks) > 0
    def complete_current_task(self):
        if self.tasks: self.tasks.pop(0); self.update_list_widget()
    def mark_current_as_processing(self, status="Przetwarzanie..."):
        if self.tasks: self.tasks[0].status = status; self.update_list_widget()
    def mark_current_as_error(self, status="Błąd"):
        if self.tasks: self.tasks[0].status = status; self.update_list_widget()
