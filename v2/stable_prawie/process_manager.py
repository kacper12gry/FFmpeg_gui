# process_manager.py
import os
from pathlib import Path
from datetime import datetime
# ZMIANA: Import z PyQt6
from PyQt6.QtCore import QProcess

class ProcessManager:
    def __init__(self, task_manager, output_window, debug_mode=False):
        self.task_manager = task_manager
        self.output_window = output_window
        self.process = None
        self.debug_mode = debug_mode
        self.log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "debug_log.txt")
        self.current_task = None

    def is_running(self):
        """Sprawdza, czy obecnie trwa jakiś proces."""
        # ZMIANA: Użycie enum ProcessState.Running
        return self.process is not None and self.process.state() == QProcess.ProcessState.Running

    def process_next_task(self):
        if not self.task_manager.has_tasks():
            return

        self.current_task = self.task_manager.get_task(0)
        if not self.current_task:
            return

        self.task_manager.mark_current_as_processing("Przetwarzanie")

        if self.current_task.selected_script == 1:
            self.run_ffmpeg(self.current_task.mkv_file)
        elif self.current_task.selected_script == 2:
            self.run_mkvmerge_ffmpeg(
                self.current_task.mkv_file,
                self.current_task.subtitle_file,
                self.current_task.font_folder
            )
        elif self.current_task.selected_script == 3:
            self.run_mkvmerge(
                self.current_task.mkv_file,
                self.current_task.subtitle_file,
                self.current_task.font_folder
            )
        elif self.current_task.selected_script == 4:
            self.run_ffmpeg_with_intro(
                self.current_task.mkv_file,
                self.current_task.intro_file
            )

    def _start_process(self, program, arguments):
        """Helper do tworzenia i uruchamiania QProcess."""
        self.output_window.clear()
        self.process = QProcess()
        # ZMIANA: Użycie enum ProcessChannelMode.MergedChannels
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.start(program, arguments)
        return self.process

    def run_mkvmerge(self, mkv_file, subtitle_file, font_folder):
        mkv_file = Path(mkv_file)
        subtitle_file = Path(subtitle_file)
        font_folder = Path(font_folder)
        final_output_file = mkv_file.with_name(mkv_file.stem + "_remux.mkv")

        arguments = ["-o", str(final_output_file), "--audio-tracks", "1", "--no-subtitles", "--no-buttons", "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_file), "--language", "0:pol", "--track-name", "0:FrixySubs", str(subtitle_file), "--attachment-mime-type", "application/x-truetype-font"]
        for font in font_folder.iterdir():
            if font.suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}:
                arguments.extend(["--attach-file", str(font)])

        process = self._start_process("mkvmerge", arguments)
        process.finished.connect(self.task_completed)
        self.task_manager.mark_current_as_processing("Uruchomiono mkvmerge")
        if self.current_task.debug_mode:
            self.log_debug(f"Uruchomiono mkvmerge z komendą: mkvmerge {' '.join(arguments)}")

    def run_mkvmerge_ffmpeg(self, mkv_file, subtitle_file, font_folder):
        mkv_file = Path(mkv_file)
        subtitle_file = Path(subtitle_file)
        font_folder = Path(font_folder)
        final_output_file = mkv_file.with_name(mkv_file.stem + "_remux.mkv")

        arguments = ["-o", str(final_output_file), "--no-subtitles", "--no-buttons", "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_file), "--language", "0:pol", "--track-name", "0:FrixySubs", str(subtitle_file), "--attachment-mime-type", "application/x-truetype-font"]
        for font in font_folder.iterdir():
            if font.suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}:
                arguments.extend(["--attach-file", str(font)])

        process = self._start_process("mkvmerge", arguments)
        process.finished.connect(lambda: self.run_ffmpeg(final_output_file, is_final=True))
        self.task_manager.mark_current_as_processing("Uruchomiono mkvmerge")
        if self.current_task.debug_mode:
            self.log_debug(f"Uruchomiono mkvmerge z komendą: mkvmerge {' '.join(arguments)}")

    def run_ffmpeg(self, mkv_file, is_final=False):
        if mkv_file is None: return
        mkv_file = Path(mkv_file)
        new_name = mkv_file.name.replace("_remux.mkv" if is_final else ".mkv", "_hardsub.mp4")
        output_file = mkv_file.with_name(new_name)
        mkv_file_str, output_file_str = str(mkv_file), str(output_file)

        if self.current_task.selected_ffmpeg_script == 1:
            arguments = ["-i", mkv_file_str, "-vf", f'format=yuv420p,subtitles=\'{mkv_file_str}\'', "-map_metadata", "-1", "-movflags", "faststart", "-c:v", "libx264", "-profile:v", "main", "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M", "-x264-params", "colormatrix=bt709", "-c:a", "copy", output_file_str]
        else:
            arguments = ["-y", "-vsync", "0", "-hwaccel", "cuda", "-i", mkv_file_str, "-vf", f'subtitles=\'{mkv_file_str}\'', "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", "-b:v", f"{self.current_task.gpu_bitrate}M", "-bufsize", "15M", "-maxrate", "15M", "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20", "-i_qfactor", "0.75", "-b_qfactor", "1.1", output_file_str]

        process = self._start_process("ffmpeg", arguments)
        if is_final or self.current_task.selected_script == 1:
            process.finished.connect(self.task_completed)

        ffmpeg_type = "CPU" if self.current_task.selected_ffmpeg_script == 1 else f"GPU (Nvidia) - {self.current_task.gpu_bitrate}M"
        self.task_manager.mark_current_as_processing(f"Uruchomiono FFmpeg ({ffmpeg_type})")
        if self.current_task.debug_mode:
            self.log_debug(f"Uruchomiono ffmpeg z komendą: ffmpeg {' '.join(arguments)}")

    def run_ffmpeg_with_intro(self, mkv_file, intro_file):
        mkv_file, intro_file = Path(mkv_file), Path(intro_file)
        output_file = mkv_file.with_name(mkv_file.stem + "_HARD.mp4")
        intro_file_str, mkv_file_str, output_file_str = str(intro_file), str(mkv_file), str(output_file)

        filter_complex = f"[1:v]subtitles='{mkv_file_str}'[v_subs];[0:v][v_subs]concat=n=2:v=1[v_out];[0:a:0][1:a:0]concat=n=2:v=0:a=1[a_out]"
        arguments = ["-i", intro_file_str, "-i", mkv_file_str, "-filter_complex", filter_complex, "-map", "[v_out]", "-map", "[a_out]", "-c:v", "libx264", "-b:v", "12M", "-bufsize", "15M", "-maxrate", "15M", "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-profile:v", "high", "-level:v", "4.1", "-tune", "animation", "-x264-params", "deblock=-2:-1:me=umh:rc-lookahead=250:qcomp=0.60:aq-mode=3:aq-strength=0.80:merange=32:ipratio=1.30:no-dct-decimate=1:vbv-bufsize=78125:vbv-maxrate=62500:coder=default:chromaoffset=0:udu_sei=false:mbtree=1:b-pyramid=2:direct=auto:trellis=1:colormatrix=bt709", "-r:v", "24000/1001", "-sar", "1:1", "-pix_fmt", "yuv420p", "-sn", "-movflags", "faststart", "-y", output_file_str]

        process = self._start_process("ffmpeg", arguments)
        process.finished.connect(self.task_completed)
        self.task_manager.mark_current_as_processing("Uruchomiono FFmpeg z wstawką")
        if self.current_task.debug_mode:
            self.log_debug(f"Uruchomiono ffmpeg z wstawką z komendą: ffmpeg {' '.join(arguments)}")

    def task_completed(self):
        self.task_manager.complete_current_task()
        self.current_task = None
        self.process = None
        self.process_next_task()

    def kill_process(self):
        # ZMIANA: Użycie enum ProcessState.Running
        if self.process and self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()
            self.process = None
            self.current_task = None

    def update_output(self):
        # ZMIANA: Konwersja QByteArray na bytes przed dekodowaniem
        output = bytes(self.process.readAll()).decode('utf-8', errors='ignore')
        self.output_window.append(output)
        if self.current_task and self.current_task.debug_mode:
            self.log_debug(output)

    def log_debug(self, message):
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")
