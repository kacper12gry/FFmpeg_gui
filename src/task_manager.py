# task_manager.py
from PyQt6.QtWidgets import QListWidgetItem
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
    output_path: Path | None = None
    status: str = "Oczekuje"

    def get_description(self, detailed: bool = False):
        if not self.mkv_file: return "Zadanie z importu (brak danych)"

        # --- WIDOK SZCZEGÓŁOWY (WIELOLINIOWY) ---
        if detailed:
            details = [f"Plik: {self.mkv_file}"]

            def path_repr_detailed(path_obj: Path | None) -> str:
                return str(path_obj) if path_obj else "Brak"

            if self.selected_script in [1, 2, 3] and self.subtitle_file:
                details.append(f"  > Napisy: {path_repr_detailed(self.subtitle_file)}")
            if self.selected_script in [1, 2, 3] and self.font_folder:
                details.append(f"  > Czcionki: {path_repr_detailed(self.font_folder)}")
            if self.selected_script == 4 and self.intro_file:
                details.append(f"  > Wstawka: {path_repr_detailed(self.intro_file)}")

            script_info = ""
            if self.selected_script == 1:
                encoder = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU ({self.gpu_bitrate} Mbps)"
                script_info = f"Typ: Hardsub | Enkoder: {encoder}"
            elif self.selected_script == 2:
                encoder = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU ({self.gpu_bitrate} Mbps)"
                script_info = f"Typ: Remux + Hardsub | Enkoder: {encoder}"
            elif self.selected_script == 3:
                script_info = "Typ: Tylko Remux"
            elif self.selected_script == 4:
                script_info = f"Typ: FFmpeg + Wstawka | Bitrate: {self.gpu_bitrate} Mbps"

            details.append(f"  > Skrypt: {script_info}")

            # --- NOWA, DODANA LINIA ---
            # Wyświetla ścieżkę wyjściową, jeśli jest niestandardowa
            if self.output_path:
                details.append(f"  > Wyjście: {path_repr_detailed(self.output_path)}")

            if self.status != "Oczekuje":
                details.append(f"  > Status: {self.status}")

            return "\n".join(details)

        # --- WIDOK STANDARDOWY (JEDNOLINIOWY, TECHNICZNY) ---
        else:
            base_description = self.mkv_file.name
            details = []

            def path_repr_simple(path_obj: Path | None) -> str:
                return path_obj.name if path_obj else "Brak"

            if self.selected_script == 1:
                encoder = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU ({self.gpu_bitrate} Mbps)"
                details.append(f"Typ: Hardsub | Enkoder: {encoder}")
            elif self.selected_script == 2:
                encoder = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU ({self.gpu_bitrate} Mbps)"
                details.append(f"Typ: Remux + Hardsub | Enkoder: {encoder}")
                details.append(f"Napisy: {path_repr_simple(self.subtitle_file)} | Czcionki: {path_repr_simple(self.font_folder)}")
            elif self.selected_script == 3:
                details.append("Typ: Tylko Remux")
                details.append(f"Napisy: {path_repr_simple(self.subtitle_file)} | Czcionki: {path_repr_simple(self.font_folder)}")
            elif self.selected_script == 4:
                details.append(f"Typ: FFmpeg + Wstawka | Bitrate: {self.gpu_bitrate} Mbps")
                details.append(f"Wstawka: {path_repr_simple(self.intro_file)}")

            if self.status != "Oczekuje":
                details.append(f"Status: {self.status}")

            return f"{base_description} | {' | '.join(details)}"


class TaskManager:
    def __init__(self, task_list_widget, process_manager, rpc_manager):
        self.tasks = []
        self.task_list_widget = task_list_widget
        self.process_manager = process_manager
        self.rpc_manager = rpc_manager
        self.detailed_view = False

    def update_list_widget(self):
        self.task_list_widget.clear()
        is_running = self.process_manager and self.process_manager.is_running()

        for i, task in enumerate(self.tasks):
            description = task.get_description(detailed=self.detailed_view)
            item = QListWidgetItem(description)

            if i == 0 and is_running:
                if self.detailed_view:
                    item.setText("► Przetwarzanie:\n" + item.text())
                else:
                    item.setText("► " + item.text())

            if "Przetwarzanie" in task.status or "Przygotowywanie" in task.status or "Krok" in task.status:
                item.setForeground(QColor("#E67E22"))
            elif "Błąd" in task.status:
                item.setForeground(QColor("#F44336"))
            self.task_list_widget.addItem(item)

    def set_detailed_view(self, enabled: bool):
        self.detailed_view = enabled
        self.update_list_widget()

    def add_task(self, mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode, intro_file, output_path=None):
        task = Task(
            mkv_file=Path(mkv_file) if mkv_file else None,
            subtitle_file=Path(subtitle_file) if subtitle_file else None,
            font_folder=Path(font_folder) if font_folder else None,
            selected_script=selected_script,
            selected_ffmpeg_script=selected_ffmpeg_script,
            gpu_bitrate=gpu_bitrate,
            debug_mode=debug_mode,
            intro_file=Path(intro_file) if intro_file else None,
            output_path=Path(output_path) if output_path else None
        )
        self.tasks.append(task)
        self.update_list_widget()

    def remove_task(self, index: int):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            self.update_list_widget()

    def get_task(self, index: int):
        return self.tasks[index] if 0 <= index < len(self.tasks) else None

    def has_tasks(self):
        return len(self.tasks) > 0

    def complete_current_task(self):
        if self.tasks:
            self.tasks.pop(0)
            self.update_list_widget()

    def mark_current_as_processing(self, status="Przetwarzanie..."):
        if self.tasks:
            self.tasks[0].status = status
            self.update_list_widget()

    def mark_current_as_error(self, status="Błąd"):
        if self.tasks and hasattr(self.tasks[0], 'status'):
            self.tasks[0].status = status
            self.update_list_widget()
