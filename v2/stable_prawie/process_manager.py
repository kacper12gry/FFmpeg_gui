# process_manager.py
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QProcess
import platform

class ProcessManager:
    def __init__(self, task_manager, output_window, debug_mode=False):
        self.task_manager = task_manager
        self.output_window = output_window
        self.process = None
        self.debug_mode = debug_mode
        self.log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "debug_log.txt")
        self.current_task = None
        self.is_windows = platform.system() == "Windows"
        self.chained_command_info = None

    def is_running(self):
        return self.process is not None and self.process.state() == QProcess.ProcessState.Running

    def _get_safe_path_for_ffmpeg(self, file_path):
        if not self.is_windows: return str(file_path)
        path_str = str(file_path).replace('\\', '\\\\').replace(':', '\\:')
        return path_str

    def process_next_task(self):
        if not self.task_manager.has_tasks() or self.is_running(): return
        self.current_task = self.task_manager.get_task(0)
        if not self.current_task: return
        self.task_manager.mark_current_as_processing("Przygotowywanie...")

        script_map = {
            1: lambda task: self.run_ffmpeg(task.mkv_file),
            2: lambda task: self.run_mkvmerge_ffmpeg(task.mkv_file, task.subtitle_file, task.font_folder),
            3: lambda task: self.run_mkvmerge(task.mkv_file, task.subtitle_file, task.font_folder),
            4: lambda task: self.run_ffmpeg_with_intro(task.mkv_file, task.intro_file)
        }
        action = script_map.get(self.current_task.selected_script)
        if action: action(self.current_task)

    def _start_process(self, program, arguments):
        self.output_window.clear()
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(self._on_process_finished)
        self.process.start(program, arguments)
        return self.process

    def _on_process_finished(self, exit_code, exit_status):
        if not self.current_task: return

        is_success = exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit

        if not is_success:
            self.task_manager.mark_current_as_error("Błąd procesu")
            # POPRAWKA: Po błędzie od razu resetujemy stan, co usunie zadanie z kolejki
            self.task_completed(success=False)
            return

        if self.chained_command_info:
            next_function = self.chained_command_info['function']
            next_args = self.chained_command_info['args']
            self.chained_command_info = None
            next_function(*next_args)
        else:
            self.task_completed(success=True)

    # ... (metody run_... pozostają bez zmian) ...
    def run_mkvmerge(self, mkv_file, subtitle_file, font_folder):
        mkv_path, subtitle_path, font_path = Path(mkv_file).resolve(), Path(subtitle_file).resolve(), Path(font_folder).resolve()
        final_output_file = mkv_path.with_name(mkv_path.stem + "_remux.mkv")
        arguments = ["-o", str(final_output_file), "--audio-tracks", "1", "--no-subtitles", "--no-buttons", "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_path), "--language", "0:pol", "--track-name", "0:FrixySubs", str(subtitle_path), "--attachment-mime-type", "application/x-truetype-font"]
        for font in font_path.iterdir():
            if font.suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}: arguments.extend(["--attach-file", str(font.resolve())])

        self.task_manager.mark_current_as_processing("Uruchomiono mkvmerge")
        if self.current_task.debug_mode: self.log_debug(f"mkvmerge {' '.join(arguments)}")
        self._start_process("mkvmerge", arguments)

    def run_mkvmerge_ffmpeg(self, mkv_file, subtitle_file, font_folder):
        mkv_path, subtitle_path, font_path = Path(mkv_file).resolve(), Path(subtitle_file).resolve(), Path(font_folder).resolve()
        final_output_file = mkv_path.with_name(mkv_path.stem + "_remux.mkv")
        arguments = ["-o", str(final_output_file), "--no-subtitles", "--no-buttons", "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_path), "--language", "0:pol", "--track-name", "0:FrixySubs", str(subtitle_path), "--attachment-mime-type", "application/x-truetype-font"]
        for font in font_path.iterdir():
            if font.suffix.lower() in {'.ttf', '.otf', '.woff', '.woff2'}: arguments.extend(["--attach-file", str(font.resolve())])

        self.chained_command_info = {'function': self.run_ffmpeg, 'args': (final_output_file, True)}
        self.task_manager.mark_current_as_processing("Krok 1/2: Uruchomiono mkvmerge")
        if self.current_task.debug_mode: self.log_debug(f"mkvmerge {' '.join(arguments)}")
        self._start_process("mkvmerge", arguments)

    def run_ffmpeg(self, mkv_file, is_final=False):
        mkv_path = Path(mkv_file).resolve()
        new_name = mkv_path.name.replace("_remux.mkv" if is_final else ".mkv", "_hardsub.mp4")
        output_file = mkv_path.with_name(new_name)
        subtitle_path_safe = self._get_safe_path_for_ffmpeg(mkv_path)
        if self.current_task.selected_ffmpeg_script == 1:
            arguments = ["-i", str(mkv_path), "-vf", f"format=yuv420p,subtitles='{subtitle_path_safe}'", "-map_metadata", "-1", "-movflags", "faststart", "-c:v", "libx264", "-profile:v", "main", "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M", "-x264-params", "colormatrix=bt709", "-c:a", "copy", str(output_file)]
        else:
            arguments = ["-y", "-vsync", "0", "-hwaccel", "cuda", "-i", str(mkv_path), "-vf", f"subtitles='{subtitle_path_safe}'", "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", "-b:v", f"{self.current_task.gpu_bitrate}M", "-bufsize", "15M", "-maxrate", "15M", "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20", "-i_qfactor", "0.75", "-b_qfactor", "1.1", str(output_file)]

        status = "Krok 2/2: Uruchomiono FFmpeg" if is_final else "Uruchomiono FFmpeg"
        self.task_manager.mark_current_as_processing(status)
        if self.current_task.debug_mode: self.log_debug(f"ffmpeg {' '.join(arguments)}")
        self._start_process("ffmpeg", arguments)

    def run_ffmpeg_with_intro(self, mkv_file, intro_file):
        mkv_path, intro_path = Path(mkv_file).resolve(), Path(intro_file).resolve()
        output_file = mkv_path.with_name(mkv_path.stem + "_HARD.mp4")
        subtitle_path_safe = self._get_safe_path_for_ffmpeg(mkv_path)
        filter_complex = f"[1:v]subtitles='{subtitle_path_safe}'[v_subs];[0:v][v_subs]concat=n=2:v=1[v_out];[0:a:0][1:a:0]concat=n=2:v=0:a=1[a_out]"
        bitrate = self.current_task.gpu_bitrate
        arguments = ["-i", str(intro_path), "-i", str(mkv_path), "-filter_complex", filter_complex, "-map", "[v_out]", "-map", "[a_out]", "-c:v", "libx264", "-b:v", f"{bitrate}M", "-bufsize", "15M", "-maxrate", "15M", "-preset", "medium", "-c:a", "aac", "-b:a", "128k", "-profile:v", "high", "-level:v", "4.1", "-tune", "animation", "-x264-params", "deblock=-2:-1:me=umh:rc-lookahead=250:qcomp=0.60:aq-mode=3:aq-strength=0.80:merange=32:ipratio=1.30:no-dct-decimate=1:vbv-bufsize=78125:vbv-maxrate=62500:coder=default:chromaoffset=0:udu_sei=false:mbtree=1:b-pyramid=2:direct=auto:trellis=1:colormatrix=bt709", "-r:v", "24000/1001", "-sar", "1:1", "-pix_fmt", "yuv420p", "-sn", "-movflags", "faststart", "-y", str(output_file)]

        self.task_manager.mark_current_as_processing("Uruchomiono FFmpeg z wstawką")
        if self.current_task.debug_mode: self.log_debug(f"ffmpeg {' '.join(arguments)}")
        self._start_process("ffmpeg", arguments)

    def task_completed(self, success=True):
        """Czyści stan po zadaniu i uruchamia następne."""
        # POPRAWKA: Zawsze usuwamy ukończone zadanie z kolejki, niezależnie od wyniku.
        # Informacja o błędzie jest już w logach i na liście (czerwony kolor).
        self.task_manager.complete_current_task()

        self.current_task = None
        self.process = None
        # Na końcu zawsze próbujemy uruchomić następne zadanie, jeśli jakieś jest.
        self.process_next_task()

    def kill_process(self):
        """Zabija bieżący proces w sposób bezpieczny i synchroniczny."""
        if self.is_running():
            self.process.finished.disconnect()
            self.process.kill()
            self.process.waitForFinished(-1)

        self.process = None
        self.current_task = None

    def update_output(self):
        if self.process:
            output = bytes(self.process.readAll()).decode('utf-8', errors='ignore')
            self.output_window.append(output)
            if self.current_task and self.current_task.debug_mode:
                self.log_debug(output)

    def log_debug(self, message):
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")
