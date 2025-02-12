import os
from pathlib import Path
from datetime import datetime
from PyQt5.QtCore import QProcess

class ProcessManager:
    def __init__(self, queue, output_window, task_list, debug_mode=False, selected_script=1, gpu_bitrate=8):
        self.queue = queue
        self.output_window = output_window
        self.task_list = task_list
        self.process = None
        self.selected_script = selected_script
        self.selected_ffmpeg_script = 1
        self.gpu_bitrate = gpu_bitrate
        self.debug_mode = debug_mode
        self.log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "debug_log.txt")

    def is_running(self):
        """Sprawdza, czy obecnie trwa jakiś proces."""
        return self.process is not None and self.process.state() == QProcess.Running

    def process_next_in_queue(self):
        if not self.queue.empty():
            mkv_file, subtitle_file, font_folder, selected_script, selected_ffmpeg_script, gpu_bitrate, debug_mode = self.queue.get()
            self.selected_script = selected_script
            self.selected_ffmpeg_script = selected_ffmpeg_script
            self.gpu_bitrate = gpu_bitrate
            self.debug_mode = debug_mode

            if self.selected_script == 1:
                self.run_ffmpeg(mkv_file)
            elif self.selected_script == 2:
                self.run_mkvmerge_ffmpeg(mkv_file, subtitle_file, font_folder)
            elif self.selected_script == 3:
                self.run_mkvmerge(mkv_file, subtitle_file, font_folder)

    def run_mkvmerge(self, mkv_file, subtitle_file, font_folder):
        mkv_file = Path(mkv_file)  # Zamiana na Path
        subtitle_file = Path(subtitle_file)  # Zamiana na Path
        font_folder = Path(font_folder)  # Zamiana na Path

        final_output_file = mkv_file.with_name(mkv_file.stem + "_remux.mkv")  # Zmiana końcówki pliku na "_remux.mkv"

        font_files = ' '.join([f'--attach-file "{font_folder / font}"' for font in font_folder.iterdir() if font.suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}])

        command = f'mkvmerge -o "{final_output_file}" --no-subtitles --no-buttons --no-track-tags --no-chapters --no-attachments "{mkv_file}" --language 0:pol --track-name 0:"FrixySubs" "{subtitle_file}" --attachment-mime-type application/x-truetype-font {font_files}'

        self.output_window.clear()  # Clear the output window before starting a new process
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.start(command)
        self.task_list.setCurrentRow(0)
        self.task_list.currentItem().setText(f"Wideo: {mkv_file}, Napisy: {subtitle_file}, Czcionki: {font_folder} (mkvmerge)")

        if self.debug_mode:
            self.log_debug(f"Started mkvmerge with command: {command}")


    def run_mkvmerge_ffmpeg(self, mkv_file, subtitle_file, font_folder):
        mkv_file = Path(mkv_file)  # Zamiana na Path
        subtitle_file = Path(subtitle_file)  # Zamiana na Path
        font_folder = Path(font_folder)  # Zamiana na Path

        final_output_file = mkv_file.with_name(mkv_file.stem + "_remux.mkv")  # Zmiana końcówki pliku na "_remux.mkv"

        font_files = ' '.join([f'--attach-file "{font_folder / font}"' for font in font_folder.iterdir() if font.suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}])

        command = f'mkvmerge -o "{final_output_file}" --no-subtitles --no-buttons --no-track-tags --no-chapters --no-attachments "{mkv_file}" --language 0:pol --track-name 0:"FrixySubs" "{subtitle_file}" --attachment-mime-type application/x-truetype-font {font_files}'

        self.output_window.clear()  # Clear the output window before starting a new process
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(lambda: self.run_ffmpeg(final_output_file, is_final=True))
        self.process.start(command)

        self.task_list.setCurrentRow(0)
        self.task_list.currentItem().setText(f"Wideo: {mkv_file}, Napisy: {subtitle_file}, Czcionki: {font_folder} (mkvmerge)")

        if self.debug_mode:
            self.log_debug(f"Started mkvmerge with command: {command}")

    def run_ffmpeg(self, mkv_file, is_final=False):
        if mkv_file is None:
            print("Błąd: mkv_file jest None, nie można przetwarzać!")
            return

        # Konwersja na Path
        mkv_file = Path(mkv_file) if not isinstance(mkv_file, Path) else mkv_file

        # Nowa nazwa pliku
        new_name = mkv_file.name.replace("_remux.mkv" if is_final else ".mkv", "_hardsub.mp4")
        output_file = mkv_file.with_name(new_name)

        # Zamiana na stringi dla QProcess
        mkv_file_str = str(mkv_file)
        output_file_str = str(output_file)

        if self.selected_ffmpeg_script == 1:
            command = [
                "ffmpeg", "-i", mkv_file_str, "-vf", f'format=yuv420p,subtitles=\'{mkv_file_str}\'',
                "-map_metadata", "-1", "-movflags", "faststart", "-c:v", "libx264", "-profile:v", "main",
                "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M",
                "-x264-params", "colormatrix=bt709", "-c:a", "copy", output_file_str
            ]
        else:
            command = [
                "ffmpeg", "-y", "-vsync", "0", "-hwaccel", "cuda", "-i", mkv_file_str, "-vf", f'subtitles=\'{mkv_file_str}\'',
                "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", f'-b:v {self.gpu_bitrate}M', "-bufsize", "15M", "-maxrate", "15M",
                "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20",
                "-i_qfactor", "0.75", "-b_qfactor", "1.1", output_file_str
            ]

        # Uruchamianie procesu FFmpeg
        self.output_window.clear()
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(self.process_next_in_queue)
        self.process.finished.connect(self.mark_task_as_done)
        self.process.start(command[0], command[1:])  # QProcess wymaga stringów

        # Aktualizacja listy zadań
        self.task_list.setCurrentRow(0)
        self.task_list.currentItem().setText(f"Wideo: {mkv_file_str} (ffmpeg) - Skrypt: {'CPU' if self.selected_ffmpeg_script == 1 else f'GPU (Nvidia) - Bitrate: {self.gpu_bitrate}M'}")

        # Debugowanie
        if self.debug_mode:
            self.log_debug(f"Started ffmpeg with command: {' '.join(command)}")

    def mark_task_as_done(self):
        # Usuń ukończone zadanie z listy
        self.task_list.takeItem(0)
        # Start the next task in the queue
        self.process_next_in_queue()

    def update_output(self):
        output = self.process.readAll().data().decode()
        self.output_window.append(output)
        if self.debug_mode:
            self.log_debug(output)

    def log_debug(self, message):
        with open(self.log_file_path, "a") as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")
