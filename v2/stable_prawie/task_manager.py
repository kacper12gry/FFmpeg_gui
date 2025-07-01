# task_manager.py
from pathlib import Path
from PyQt6.QtWidgets import QListWidgetItem

class Task:
    def __init__(self, mkv_file, subtitle_file, font_folder,
                 selected_script, selected_ffmpeg_script,
                 gpu_bitrate, debug_mode, intro_file):
        self.mkv_file = Path(mkv_file) if mkv_file else None
        self.subtitle_file = Path(subtitle_file) if subtitle_file else None
        self.font_folder = Path(font_folder) if font_folder else None
        self.selected_script = selected_script
        self.selected_ffmpeg_script = selected_ffmpeg_script
        self.gpu_bitrate = gpu_bitrate
        self.debug_mode = debug_mode
        self.intro_file = Path(intro_file) if intro_file else None

    def get_description(self):
        if self.selected_script == 1:
            ffmpeg_type = "CPU" if self.selected_ffmpeg_script == 1 else f"GPU (Nvidia) - Bitrate: {self.gpu_bitrate}M"
            return f"FFmpeg: Wideo: {self.mkv_file.name}, Kodowanie: {ffmpeg_type}"
        elif self.selected_script in [2, 3]:
            script_type = "mkvmerge + FFmpeg" if self.selected_script == 2 else "Tylko mkvmerge"
            return f"{script_type}: Wideo: {self.mkv_file.name}, Napisy: {self.subtitle_file.name}"
        elif self.selected_script == 4:
            return f"FFmpeg+Wstawka: Wideo: {self.mkv_file.name}, Intro: {self.intro_file.name}"
        else:
            return "Nieznane zadanie"

class TaskManager:
    def __init__(self, task_list_widget):
        self.task_list_widget = task_list_widget
        self.tasks = []

    def add_task(self, mkv_file, subtitle_file, font_folder,
                selected_script, selected_ffmpeg_script,
                gpu_bitrate, debug_mode, intro_file):
        task = Task(
            mkv_file, subtitle_file, font_folder,
            selected_script, selected_ffmpeg_script,
            gpu_bitrate, debug_mode, intro_file
        )
        self.tasks.append(task)
        item = QListWidgetItem(task.get_description())
        self.task_list_widget.addItem(item)
        return task

    def get_task(self, index):
        if 0 <= index < len(self.tasks):
            return self.tasks[index]
        return None

    def remove_task(self, index):
        if 0 <= index < len(self.tasks):
            self.tasks.pop(index)
            self.task_list_widget.takeItem(index)

    def has_tasks(self):
        return len(self.tasks) > 0

    def mark_current_as_processing(self, status_text=None):
        if self.has_tasks():
            item = self.task_list_widget.item(0)
            if item:
                if status_text:
                    item.setText(f"{self.tasks[0].get_description()} - {status_text}")
                self.task_list_widget.setCurrentRow(0)

    def complete_current_task(self):
        if self.has_tasks():
            self.remove_task(0)

    def get_task_count(self):
        return len(self.tasks)
