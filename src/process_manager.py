# process_manager.py
import os
import re
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QObject, QProcess, pyqtSignal
import platform
import subprocess

class ProcessManager(QObject):
    eta_updated = pyqtSignal(int)
    log_message = pyqtSignal(str)
    def __init__(self, task_manager, output_window, rpc_manager, debug_mode=False):
        super().__init__()
        self.task_manager = task_manager
        self.output_window = output_window
        self.rpc_manager = rpc_manager
        self.process = None
        self.debug_mode = debug_mode
        self.log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "debug_log.txt")
        self.current_task = None
        self.is_windows = platform.system() == "Windows"
        self.chained_command_info = None
        self.total_duration_seconds = 0
        self.start_time = None
        self.current_ffmpeg_speed = None

    def _start_process(self, program, arguments):
        if self.process is None:
            self.output_window.clear()
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(self._on_process_finished)
        self.process.start(program, arguments)
        self.task_manager.update_list_widget()
        return self.process

    def _run_ffprobe_command(self, command):
        try:
            if self.is_windows:
                # Ukryj okno konsoli w systemie Windows
                result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=10)
            return result.stdout.strip()
        except Exception as e:
            self.log_debug(f"Błąd ffprobe: {e}")
            return None

    # --- KRYTYCZNA POPRAWKA ---
    def _get_video_duration(self, video_path):
        if not video_path:
            return 0.0
        command = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)]
        duration_str = self._run_ffprobe_command(command)

        try:
            return float(duration_str)
        except (ValueError, TypeError):
            self.log_message.emit(f"OSTRZEŻENIE: Nie udało się odczytać czasu trwania z pliku '{video_path.name}'. Może być uszkodzony.")
            return 0.0

    def _get_video_framerate(self, video_path):
        if not video_path:
            return None
        command = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=r_frame_rate', '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)]
        return self._run_ffprobe_command(command)

    def _parse_ffmpeg_time(self, output):
        speed_match = re.search(r"speed=\s*([\d.]+)x", output)
        if speed_match:
            self.current_ffmpeg_speed = f"{speed_match.group(1)}x"
        if not self.total_duration_seconds or not self.start_time:
            return
        time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})", output)
        if time_match:
            h, m, s, _ = map(int, time_match.groups())
            processed_seconds = h * 3600 + m * 60 + s
            if processed_seconds > 0:
                elapsed_time = (datetime.now() - self.start_time).total_seconds()
                processing_speed = processed_seconds / elapsed_time
                if processing_speed > 0:
                    eta_seconds = int((self.total_duration_seconds - processed_seconds) / processing_speed)
                    self.eta_updated.emit(eta_seconds)

    def process_next_task(self):
        if not self.task_manager.has_tasks() or self.is_running():
            return

        self.current_task = self.task_manager.get_task(0)
        if not self.current_task:
            return

        self.debug_mode = self.current_task.debug_mode
        self.log_terminal("process_next_task called.")

        if not self.task_manager.has_tasks() or self.is_running():
            self.log_terminal("No tasks to process or a process is already running.")
            return

        self.log_terminal(f"Current task script ID: {self.current_task.selected_script}")
        self.log_terminal(f"Current task encoder ID: {self.current_task.selected_ffmpeg_script}")

        self.total_duration_seconds = self._get_video_duration(self.current_task.mkv_file)
        self.start_time = datetime.now()
        self.task_manager.mark_current_as_processing("Przygotowywanie...")
        script_map = {
            1: lambda task: self.run_ffmpeg(task.mkv_file),
            2: lambda task: self.run_mkvmerge_ffmpeg(task.mkv_file, task.subtitle_file, task.font_folder),
            3: lambda task: self.run_mkvmerge(task.mkv_file, task.subtitle_file, task.font_folder),
            4: lambda task: self.run_ffmpeg_with_intro(task.mkv_file, task.intro_file)
        }
        action = script_map.get(self.current_task.selected_script)
        if action:
            self.log_terminal("Action found, executing...")
            action(self.current_task)
        else:
            self.log_terminal(f"No action found for script ID: {self.current_task.selected_script}")

    def _on_process_finished(self, exit_code, exit_status):
        is_success = exit_code == 0 and exit_status == QProcess.ExitStatus.NormalExit
        if self.chained_command_info and is_success:
            next_function, next_args = self.chained_command_info['function'], self.chained_command_info['args']
            self.chained_command_info = None
            next_function(*next_args)
        elif self.current_task:
            if not is_success:
                self.task_manager.mark_current_as_error("Błąd procesu")
            self.task_completed(success=is_success)
        else:
            self.output_window.append(">>> Proces zakończony.")
            self.process = None

    def task_completed(self, success=True):
        self.eta_updated.emit(-1)
        self.current_ffmpeg_speed = None
        if self.current_task:
            self.task_manager.complete_current_task()
        self.current_task = None
        self.process = None
        self.process_next_task()

    def kill_process(self):
        self.eta_updated.emit(-1)
        self.current_ffmpeg_speed = None
        if self.is_running():
            self.process.finished.disconnect()
            self.process.kill()
            self.process.waitForFinished(-1)
        self.process = None
        self.current_task = None

    def kill_process_and_advance(self):
        self.kill_process()
        self.process_next_task()

    def run_mkvmerge(self, mkv_file, subtitle_file, font_folder):
        mkv_path, _, font_path = Path(mkv_file), Path(subtitle_file), Path(font_folder)

        # Integracja niestandardowej ścieżki
        if self.current_task and self.current_task.output_path:
            output_file = self.current_task.output_path
        else:
            output_file = mkv_path.with_name(f"{mkv_path.stem}_remux.mkv")

        program = "mkvmerge"
        # --- TWOJA POPRAWNA LOGIKA ---
        track_name = self.current_task.subtitle_track_name.strip() or ""
        movie_name = self.current_task.movie_name
        args = ["-o", str(output_file), "--audio-tracks", "1", "--no-subtitles",
                "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_file),
                "--language", "0:pol", "--track-name", f"0:{track_name}", str(subtitle_file)]
        if movie_name == " ":
            pass
        elif movie_name:
            args.extend(["--title", movie_name])
        else:
            args.extend(["--title", ""])
        # -----------------------------

        if font_path.is_dir():
            for font in font_path.iterdir():
                if font.suffix.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
                    args.extend(["--attach-file", str(font)])
        if self.debug_mode:
            self.log_debug(f"Running command: {program} {' '.join(args)}")
        self.task_manager.mark_current_as_processing("Uruchomiono mkvmerge")
        self._start_process(program, args)

    def run_mkvmerge_ffmpeg(self, mkv_file, subtitle_file, font_folder):
        output_file_remux = Path(mkv_file).with_name(f"{Path(mkv_file).stem}_remux.mkv")
        self.chained_command_info = {'function': self.run_ffmpeg, 'args': (output_file_remux, True)}

        _, _, font_path = Path(mkv_file), Path(subtitle_file), Path(font_folder)
        program = "mkvmerge"
        # --- TWOJA POPRAWNA LOGIKA ---
        track_name = self.current_task.subtitle_track_name.strip() or ""
        movie_name = self.current_task.movie_name
        # --- MAŁA KOREKTA ZMIENNEJ ---
        args = ["-o", str(output_file_remux), "--audio-tracks", "1", "--no-subtitles",
                "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_file),
                "--language", "0:pol", "--track-name", f"0:{track_name}", str(subtitle_file)]
        if movie_name == " ":
            pass
        elif movie_name:
            args.extend(["--title", movie_name])
        else:
            args.extend(["--title", ""])
        # -----------------------------

        if font_path.is_dir():
            for font in font_path.iterdir():
                if font.suffix.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
                    args.extend(["--attach-file", str(font)])
        if self.debug_mode:
            self.log_debug(f"Running command: {program} {' '.join(args)}")
        self.task_manager.mark_current_as_processing("Krok 1/2: Uruchomiono mkvmerge")
        self._start_process(program, args)


    def is_running(self):
        return self.process is not None and self.process.state() == QProcess.ProcessState.Running

    def _get_safe_path_for_ffmpeg(self, file_path):
        if not self.is_windows:
            return str(file_path)
        return str(file_path).replace('\\', '\\\\').replace(':', '\\:')

    def update_output(self):
        if self.process:
            output = bytes(self.process.readAll()).decode('utf-8', errors='ignore')
            self.output_window.append(output)
            self._parse_ffmpeg_time(output)
            if self.debug_mode:
                self.log_debug(output)

    def run_ffmpeg(self, mkv_file, is_final=False):
        mkv_path = Path(mkv_file)
        subtitle_path = self._get_safe_path_for_ffmpeg(mkv_path)

        # Integracja niestandardowej ścieżki
        if is_final and self.current_task and self.current_task.output_path:
            output_file = self.current_task.output_path
        else:
            output_file = mkv_path.with_name(mkv_path.name.replace("_remux.mkv" if is_final else ".mkv", "_hardsub.mp4"))

        subtitle_path = self._get_safe_path_for_ffmpeg(mkv_path)

        program = "ffmpeg"
        if self.current_task.selected_ffmpeg_script == 1: # CPU
            args = ["-i", str(mkv_path), "-vf", f"format=yuv420p,subtitles='{subtitle_path}'", "-map_metadata", "-1", "-movflags", "+faststart", "-c:v", "libx264", "-profile:v", "main", "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M", "-x264-params", "colormatrix=bt709", "-c:a", "copy", str(output_file)]
        elif self.current_task.selected_ffmpeg_script == 2: # GPU (CUDA)
            args = ["-y", "-vsync", "0", "-hwaccel", "cuda", "-i", str(mkv_path), "-vf", f"subtitles='{subtitle_path}'", "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", "-b:v", f"{self.current_task.gpu_bitrate}M", "-bufsize", "15M", "-maxrate", "15M", "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20", "-i_qfactor", "0.75", "-b_qfactor", "1.1", str(output_file)]
        elif self.current_task.selected_ffmpeg_script == 3: # GPU (VA-API)
            args = ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi", "-i", str(mkv_path), "-vf", f"subtitles='{subtitle_path}',format=nv12,hwupload", "-c:a", "copy", "-c:v", "h264_vaapi", "-b:v", f"{self.current_task.gpu_bitrate}M", str(output_file)]

        if self.debug_mode:
            self.log_debug(f"Running command: {program} {' '.join(args)}")
        status = "Krok 2/2: Uruchomiono FFmpeg" if is_final else "Uruchomiono FFmpeg"
        self.task_manager.mark_current_as_processing(status)
        self._start_process(program, args)

    def run_ffmpeg_with_intro(self, mkv_file, intro_file):
        self.log_terminal("run_ffmpeg_with_intro called.")
        mkv_path, intro_path = Path(mkv_file), Path(intro_file)

        if self.current_task and self.current_task.output_path:
            output_file = self.current_task.output_path
        else:
            output_file = mkv_path.with_name(f"{mkv_path.stem}_HARD.mp4")

        program = "ffmpeg"
        subtitle_path = self._get_safe_path_for_ffmpeg(mkv_path)
        bitrate = self.current_task.gpu_bitrate
        framerate = self._get_video_framerate(mkv_path)
        framerate_arg = ["-r:v", framerate] if framerate else []

        audio_filter = "[0:a:0]loudnorm=I=-20:LRA=10:tp=-1.8[a_intro_norm];[1:a:0]loudnorm=I=-20:LRA=10:tp=-1.8[a_main_norm];[a_intro_norm][a_main_norm]concat=n=2:v=0:a=1[a_out]"

        args = [] # Initialize args
        self.log_terminal("Constructing args...")

        if self.current_task.selected_ffmpeg_script == 1:
            self.log_terminal("Using CPU path for intro script.")
            filter_complex_cpu = (
                f"[1:v]subtitles='{subtitle_path}'[v_subs];"
                f"[0:v][v_subs]concat=n=2:v=1[v_out];{audio_filter}"
            )
            x264_params = (
                "deblock=-2:-1:me=umh:rc-lookahead=250:qcomp=0.60:aq-mode=3:aq-strength=0.80:"
                "merange=32:ipratio=1.30:no-dct-decimate=1:vbv-bufsize=78125:vbv-maxrate=62500:"
                "coder=default:chromaoffset=0:udu_sei=false:mbtree=1:b-pyramid=2:direct=auto:"
                "trellis=1:colormatrix=bt709"
            )
            args = [
                "-i", str(intro_path), "-i", str(mkv_path),
                "-filter_complex", filter_complex_cpu,
                "-map", "[v_out]", "-map", "[a_out]",
                "-c:v", "libx264", "-b:v", f"{bitrate}M",
                "-bufsize", "15M", "-maxrate", "15M", "-preset", "medium",
                "-c:a", "aac", "-b:a", "128k",
                "-profile:v", "high", "-level:v", "4.1", "-tune", "animation",
                "-x264-params", x264_params, *framerate_arg, "-sar", "1:1",
                "-pix_fmt", "yuv420p", "-sn", "-movflags", "faststart", "-y", str(output_file)
            ]

        elif self.current_task.selected_ffmpeg_script in [2, 3]:
            self.log_terminal("Using GPU path for intro script.")
            video_filter_cpu = f"[1:v]subtitles='{subtitle_path}'[v_subs];[0:v][v_subs]concat=n=2:v=1:a=0[v_cpu]"
            
            if self.current_task.selected_ffmpeg_script == 2:
                self.log_terminal("Using CUDA path.")
                hw_accel_args = ["-hwaccel", "cuda"]
                filter_complex = f"{video_filter_cpu};[v_cpu]hwupload_cuda[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "h264_nvenc", "-preset", "p2"]

            else: # selected_ffmpeg_script == 3
                self.log_terminal("Using VA-API path.")
                hw_accel_args = ["-hwaccel", "vaapi"]
                filter_complex = f"{video_filter_cpu};[v_cpu]format=nv12,hwupload[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "h264_vaapi", "-profile:v", "high"]

            args = [
                *hw_accel_args,
                "-i", str(intro_path), "-i", str(mkv_path),
                "-filter_complex", filter_complex,
                "-map", "[v_out]", "-map", "[a_out]",
                *video_codec_args,
                "-b:v", f"{bitrate}M", "-bufsize", "15M", "-maxrate", "15M",
                *framerate_arg,
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart", "-y", str(output_file)
            ]
        
        if not args:
            self.log_terminal("ERROR - args list is empty. No path taken.")
            return

        self.log_terminal("Args constructed. About to start process.")
        self.log_terminal(f"Final args list: {args}")

        if self.debug_mode:
            self.log_debug(f"Running command: {program} {' '.join(args)}")
        self.task_manager.mark_current_as_processing("Uruchomiono FFmpeg z wstawką")
        self._start_process(program, args)

    def log_debug(self, message):
        if not self.debug_mode:
            return
        # Poprawka zapewniająca tworzenie katalogu logów
        log_dir = os.path.dirname(self.log_file_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")

    def log_terminal(self, message):
        if self.debug_mode:
            print(f"DEBUG: {message}")

