# process_manager.py
import os
import re
import json
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QStandardPaths
import platform
import subprocess

class ProcessManager(QObject):
    eta_updated = pyqtSignal(int)
    log_message = pyqtSignal(str)
    queue_finished = pyqtSignal()

    def __init__(self, task_manager, output_window, rpc_manager, debug_mode=False):
        super().__init__()
        self.task_manager = task_manager
        self.output_window = output_window
        self.rpc_manager = rpc_manager
        self.process = None
        self.debug_mode = False # Domyślnie, ustawiane per zadanie
        log_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        self.log_file_path = os.path.join(log_dir, "debug_log.txt")
        
        # Upewnij się, że katalog logów istnieje raz na starcie
        os.makedirs(log_dir, exist_ok=True)
        
        self.current_task = None
        self.is_windows = platform.system() == "Windows"
        self.chained_command_info = None
        self.total_duration_seconds = 0
        self.start_time = None
        self.current_ffmpeg_speed = None
        self.eta_seconds = -1
        self.progress_percentage = -1.0

    def _start_process(self, program, arguments):
        if self.process is not None:
            # Jeśli istnieje stary proces, odłącz go i zakończ przed startem nowego
            try:
                self.process.finished.disconnect()
            except: pass
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()
            self.process.deleteLater()

        self.output_window.clear()
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(self._on_process_finished)
        self.process.start(program, arguments)
        self.task_manager.update_list_widget()
        return self.process

    def _run_ffprobe_async(self, command, callback):
        """Uruchamia ffprobe asynchronicznie za pomocą QProcess."""
        probe_process = QProcess(self)
        probe_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        
        def on_finished():
            output = bytes(probe_process.readAll()).decode('utf-8', errors='ignore').strip()
            probe_process.deleteLater()
            callback(output)

        probe_process.finished.connect(on_finished)
        probe_process.start(command[0], command[1:])

    def process_next_task(self):
        if not self.task_manager.has_tasks() or self.is_running():
            return

        self.current_task = self.task_manager.get_task(0)
        if not self.current_task:
            return

        self.debug_mode = self.current_task.debug_mode
        self.log_terminal("process_next_task called. Gathering metadata...")

        self.task_manager.mark_current_as_processing("Pobieranie metadanych...")

        # Pobieramy czas trwania i framerate w jednym wywołaniu (format JSON dla łatwego parsowania)
        probe_cmd = [
            'ffprobe', '-v', 'error', 
            '-select_streams', 'v:0', 
            '-show_entries', 'format=duration:stream=r_frame_rate', 
            '-of', 'json', 
            str(self.current_task.mkv_file)
        ]
        
        def on_metadata_ready(json_output):
            duration = 0.0
            framerate = None
            try:
                data = json.loads(json_output)
                if 'format' in data and 'duration' in data['format']:
                    duration = float(data['format']['duration'])
                if 'streams' in data and len(data['streams']) > 0:
                    framerate = data['streams'][0].get('r_frame_rate')
            except Exception as e:
                self.log_terminal(f"Błąd parsowania metadanych: {e}")
            
            self.total_duration_seconds = duration
            self._current_task_framerate = framerate # Zapamiętaj framerate dla skryptów
            self._continue_task_execution()

        self._run_ffprobe_async(probe_cmd, on_metadata_ready)

    def _continue_task_execution(self):
        """Kontynuuje wykonywanie zadania po pobraniu metadanych."""
        self.start_time = datetime.now()
        
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
        self.eta_seconds = -1
        self.progress_percentage = -1.0
        if self.current_task:
            self.task_manager.complete_current_task()
        self.current_task = None
        self.process = None
        
        # Sprawdź, czy są kolejne zadania, jeśli nie, zakończono kolejkę
        if not self.task_manager.has_tasks():
            self.queue_finished.emit()
        else:
            self.process_next_task()

    def kill_process(self):
        """Mocne i pewne zakończenie procesu."""
        self.eta_updated.emit(-1)
        self.current_ffmpeg_speed = None
        self.eta_seconds = -1
        self.progress_percentage = -1.0
        
        if self.process:
            try:
                self.process.finished.disconnect()
            except: pass
            
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.terminate() # Najpierw grzecznie
                if not self.process.waitForFinished(1000):
                    self.process.kill() # Potem brutalnie
                    self.process.waitForFinished(1000)
            
            self.process.deleteLater()
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
        audio_id = str(self.current_task.selected_audio_track_id) if self.current_task.selected_audio_track_id is not None else "0"

        args = ["-o", str(output_file), "--audio-tracks", audio_id, "--no-subtitles",
                "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_file),
                "--language", "0:pol", "--track-name", f"0:{track_name}", str(subtitle_file)]
        if self.current_task.keep_original_movie_name:
            pass # Nie dodawaj flagi --title, zachowaj oryginał
        elif movie_name:
            args.extend(["--title", movie_name])
        else:
            args.extend(["--title", ""]) # Wyczyść tytuł, jeśli pole jest puste i nie zaznaczono "zachowaj"
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
        audio_id = str(self.current_task.selected_audio_track_id) if self.current_task.selected_audio_track_id is not None else "0"

        # --- MAŁA KOREKTA ZMIENNEJ ---
        args = ["-o", str(output_file_remux), "--audio-tracks", audio_id, "--no-subtitles",
                "--no-track-tags", "--no-chapters", "--no-attachments", str(mkv_file),
                "--language", "0:pol", "--track-name", f"0:{track_name}", str(subtitle_file)]
        if self.current_task.keep_original_movie_name:
            pass # Nie dodawaj flagi --title, zachowaj oryginał
        elif movie_name:
            args.extend(["--title", movie_name])
        else:
            args.extend(["--title", ""]) # Wyczyść tytuł, jeśli pole jest puste i nie zaznaczono "zachowaj"
        # -----------------------------

        if font_path.is_dir():
            for font in font_path.iterdir():
                if font.suffix.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
                    args.extend(["--attach-file", str(font)])
        if self.debug_mode:
            self.log_debug(f"Running command: {program} {' '.join(args)}")
        self.task_manager.mark_current_as_processing("Krok 1/2: Uruchomiono mkvmerge")
        self._start_process(program, args)


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

            if self.total_duration_seconds > 0:
                self.progress_percentage = (processed_seconds / self.total_duration_seconds) * 100
            else:
                self.progress_percentage = 0

            if processed_seconds > 0:
                elapsed_time = (datetime.now() - self.start_time).total_seconds()
                processing_speed = processed_seconds / elapsed_time
                if processing_speed > 0:
                    eta_seconds = int((self.total_duration_seconds - processed_seconds) / processing_speed)
                    self.eta_seconds = eta_seconds
                    self.eta_updated.emit(eta_seconds)

    def is_running(self):
        return self.process is not None and self.process.state() == QProcess.ProcessState.Running

    def _get_safe_path_for_ffmpeg(self, file_path):
        # Konwersja na ciąg znaków
        path_str = str(file_path)
        
        # Escape'owanie znaków specjalnych dla filtru FFmpeg na wszystkich platformach:
        # 1. Backslash (znak ucieczki) - musi być pierwszy!
        path_str = path_str.replace('\\', '\\\\')
        # 2. Dwukropek (separator opcji w filtrach)
        path_str = path_str.replace(':', '\\:')
        # 3. Apostrof (separator ciągu znaków)
        path_str = path_str.replace("'", "\\'")
        # 4. Nawiasy kwadratowe (mogą być interpretowane jako tagi w grafie filtrów)
        path_str = path_str.replace('[', '\\[').replace(']', '\\]')
        
        return path_str

    def update_output(self):
        if self.process:
            output = bytes(self.process.readAll()).decode('utf-8', errors='ignore')
            # Używamy insertPlainText zamiast append, aby uniknąć zbędnych nowych linii
            # i zachować naturalny przepływ tekstu z procesu.
            cursor = self.output_window.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.insertText(output)
            self.output_window.setTextCursor(cursor)
            self.output_window.ensureCursorVisible()
            
            self._parse_ffmpeg_time(output)
            if self.debug_mode:
                self.log_debug(output)

    def run_ffmpeg(self, mkv_file, is_final=False):
        mkv_path = Path(mkv_file)
        
        # Integracja niestandardowej ścieżki
        if is_final and self.current_task and self.current_task.output_path:
            output_file = self.current_task.output_path
        else:
            # Używamy suffix/with_suffix dla bezpieczniejszej zamiany rozszerzenia
            new_name = mkv_path.name.replace("_remux.mkv", "_hardsub.mp4") if "_remux.mkv" in mkv_path.name else mkv_path.with_suffix(".mp4").name.replace(".mp4", "_hardsub.mp4")
            output_file = mkv_path.with_name(new_name)

        subtitle_path = self._get_safe_path_for_ffmpeg(mkv_path)

        program = "ffmpeg"
        args = [] # Domyślnie pusta lista
        
        if self.current_task.selected_ffmpeg_script == 1: # CPU
            args = ["-i", str(mkv_path), "-vf", f"format=yuv420p,subtitles='{subtitle_path}'", "-map_metadata", "-1", "-movflags", "+faststart", "-c:v", "libx264", "-profile:v", "main", "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M", "-x264-params", "colormatrix=bt709", "-c:a", "copy", str(output_file)]
        elif self.current_task.selected_ffmpeg_script == 2: # GPU (CUDA)
            args = ["-y", "-vsync", "0", "-hwaccel", "cuda", "-i", str(mkv_path), "-vf", f"subtitles='{subtitle_path}'", "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", "-b:v", f"{self.current_task.gpu_bitrate}M", "-bufsize", "15M", "-maxrate", "15M", "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20", "-i_qfactor", "0.75", "-b_qfactor", "1.1", str(output_file)]
        elif self.current_task.selected_ffmpeg_script == 3: # GPU (VA-API)
            args = ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi", "-i", str(mkv_path), "-vf", f"subtitles='{subtitle_path}',format=nv12,hwupload", "-c:a", "copy", "-c:v", "h264_vaapi", "-b:v", f"{self.current_task.gpu_bitrate}M", str(output_file)]
        elif self.current_task.selected_ffmpeg_script == 4: # GPU (VA-API AV1)
            args = ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi", "-i", str(mkv_path), "-vf", f"subtitles='{subtitle_path}',format=nv12,hwupload", "-c:a", "copy", "-c:v", "av1_vaapi", "-b:v", f"{self.current_task.gpu_bitrate}M", str(output_file)]

        if not args:
            self.log_message.emit("BŁĄD: Nie wybrano poprawnego enkodera FFmpeg.")
            self.task_completed(success=False)
            return

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
        
        # Użyj framerate pobranego wcześniej asynchronicznie
        framerate = getattr(self, '_current_task_framerate', None)
        framerate_arg = ["-r:v", framerate] if framerate else []

        audio_filter = "[0:a:0]loudnorm=I=-20:LRA=10:tp=-1.8[a_intro_norm];[1:a:0]loudnorm=I=-20:LRA=10:tp=-1.8[a_main_norm];[a_intro_norm][a_main_norm]concat=n=2:v=0:a=1[a_out]"

        # Skrypt dla CPU
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

        # Skrypty dla GPU (CUDA lub VA-API)
        elif self.current_task.selected_ffmpeg_script in [2, 3, 4]:
            self.log_terminal("Using GPU path for intro script.")
            video_filter_cpu = f"[1:v]subtitles='{subtitle_path}'[v_subs];[0:v][v_subs]concat=n=2:v=1:a=0[v_cpu]"
            
            if self.current_task.selected_ffmpeg_script == 2:
                self.log_terminal("Using CUDA path.")
                hw_accel_args = ["-hwaccel", "cuda"]
                filter_complex = f"{video_filter_cpu};[v_cpu]hwupload_cuda[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "h264_nvenc", "-preset", "p2"]

            elif self.current_task.selected_ffmpeg_script == 3:
                self.log_terminal("Using VA-API H264 path.")
                hw_accel_args = ["-hwaccel", "vaapi"]
                filter_complex = f"{video_filter_cpu};[v_cpu]format=nv12,hwupload[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "h264_vaapi", "-profile:v", "high"]
            
            elif self.current_task.selected_ffmpeg_script == 4:
                self.log_terminal("Using VA-API AV1 path.")
                hw_accel_args = ["-hwaccel", "vaapi"]
                filter_complex = f"{video_filter_cpu};[v_cpu]format=nv12,hwupload[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "av1_vaapi"]

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
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")

    def log_terminal(self, message):
        if self.debug_mode:
            print(f"DEBUG: {message}")

