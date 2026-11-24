# process_manager.py
import os
import re
import json
import shlex
import subprocess
from pathlib import Path
from datetime import datetime
from PyQt6.QtCore import QObject, QProcess, pyqtSignal, QStandardPaths
import platform

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
        self._probing = False   # trwa pobieranie metadanych (ffprobe) - zadanie 0 jest już aktywne
        self._probe_id = 0      # unieważnia spóźnioną odpowiedź ffprobe po anulowaniu
        self.vaapi_device = self._detect_vaapi_device()
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
        """Uruchamia ffprobe asynchronicznie za pomocą QProcess. callback wołany dokładnie raz."""
        probe_process = QProcess(self)
        probe_process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        done = False

        def finish(output):
            nonlocal done
            if done:
                return
            done = True
            probe_process.deleteLater()
            callback(output)

        def on_finished():
            finish(bytes(probe_process.readAll()).decode('utf-8', errors='ignore').strip())

        def on_error(error):
            # Bez tego brak ffprobe zawieszał kolejkę na "Pobieranie metadanych..."
            if error == QProcess.ProcessError.FailedToStart:
                finish("")

        probe_process.finished.connect(on_finished)
        probe_process.errorOccurred.connect(on_error)
        probe_process.start(command[0], command[1:])

    def process_next_task(self):
        if not self.task_manager.has_tasks() or self.is_running():
            return

        self.current_task = self.task_manager.get_task(0)
        if not self.current_task:
            return

        self.debug_mode = self.current_task.debug_mode
        self.chained_command_info = None   # każde zadanie zaczyna bez zaległego kroku 2/2
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
        
        self._probe_id += 1
        probe_id = self._probe_id
        self._probing = True

        def on_metadata_ready(json_output):
            if probe_id != self._probe_id:
                return   # zadanie anulowane w trakcie ffprobe - ignoruj spóźnioną odpowiedź
            self._probing = False
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
        missing = self._missing_inputs(self.current_task)
        if missing:
            # Zadanie z importu TXT może mieć puste ścieżki - bez tego kolejka zawisałaby na wyjątku.
            self.output_window.append(f">>> Pominięto zadanie - brak wymaganych danych: {', '.join(missing)}.")
            self.task_manager.mark_current_as_error("Błąd: brak danych")
            self.task_completed(success=False)
            return
        action = script_map.get(self.current_task.selected_script)
        if action:
            self.log_terminal("Action found, executing...")
            action(self.current_task)
        else:
            self.log_terminal(f"No action found for script ID: {self.current_task.selected_script}")

    @staticmethod
    def _missing_inputs(task):
        """Nazwy pól wymaganych przez wybrany skrypt, które w zadaniu są puste."""
        required = {1: [("plik MKV", task.mkv_file)],
                    2: [("plik MKV", task.mkv_file), ("napisy", task.subtitle_file), ("folder czcionek", task.font_folder)],
                    3: [("plik MKV", task.mkv_file), ("napisy", task.subtitle_file), ("folder czcionek", task.font_folder)],
                    4: [("plik MKV", task.mkv_file), ("wstawka", task.intro_file)]}
        return [name for name, value in required.get(task.selected_script, []) if not value]

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
        self._probe_id += 1     # unieważnij ewentualny trwający ffprobe
        self._probing = False
        self.chained_command_info = None   # bez tego krok 2/2 anulowanego zadania odpalał się po następnym zadaniu
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

    # ------------------------------------------------------------------
    # Budowanie komend - czyste funkcje (bez uruchamiania procesów).
    # Używane zarówno przy prawdziwym uruchomieniu, jak i w "Podglądzie komendy",
    # dzięki czemu podgląd zawsze pokazuje dokładnie to, co zostanie odpalone.
    # ------------------------------------------------------------------

    @staticmethod
    def format_command(program, args):
        """Komenda jako jeden tekst gotowy do wklejenia w terminal (poprawne cudzysłowy)."""
        parts = [str(program), *(str(a) for a in args)]
        if platform.system() == "Windows":
            return subprocess.list2cmdline(parts)
        return shlex.join(parts)

    @staticmethod
    def _remux_output_path(mkv_file):
        mkv_path = Path(mkv_file)
        return mkv_path.with_name(f"{mkv_path.stem}_remux.mkv")

    def _build_mkvmerge(self, task, output_file):
        font_path = Path(task.font_folder)
        track_name = task.subtitle_track_name.strip() or ""
        audio_id = str(task.selected_audio_track_id) if task.selected_audio_track_id is not None else "0"

        args = ["-o", str(output_file), "--audio-tracks", audio_id, "--no-subtitles",
                "--no-track-tags", "--no-chapters", "--no-attachments", str(task.mkv_file),
                "--language", "0:pol", "--track-name", f"0:{track_name}", str(task.subtitle_file)]
        if task.keep_original_movie_name:
            pass # Nie dodawaj flagi --title, zachowaj oryginał
        elif task.movie_name:
            args.extend(["--title", task.movie_name])
        else:
            args.extend(["--title", ""]) # Wyczyść tytuł, jeśli pole jest puste i nie zaznaczono "zachowaj"

        if font_path.is_dir():
            for font in sorted(font_path.iterdir()):
                if font.suffix.lower() in ['.ttf', '.otf', '.woff', '.woff2']:
                    args.extend(["--attach-file", str(font)])
        return "mkvmerge", args

    def _build_ffmpeg(self, task, mkv_file, is_final=False):
        """Zwraca (program, args) albo None, jeśli enkoder jest niepoprawny."""
        mkv_path = Path(mkv_file)

        # Integracja niestandardowej ścieżki
        if is_final and task.output_path:
            output_file = task.output_path
        else:
            # Używamy suffix/with_suffix dla bezpieczniejszej zamiany rozszerzenia
            new_name = mkv_path.name.replace("_remux.mkv", "_hardsub.mp4") if "_remux.mkv" in mkv_path.name else mkv_path.with_suffix(".mp4").name.replace(".mp4", "_hardsub.mp4")
            output_file = mkv_path.with_name(new_name)

        subs = self._subtitles_filter(task, mkv_path)
        encoder = task.selected_ffmpeg_script

        if encoder == 1: # CPU
            args = ["-i", str(mkv_path), "-vf", f"format=yuv420p,{subs}", "-map_metadata", "-1", "-movflags", "+faststart", "-c:v", "libx264", "-profile:v", "main", "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M", "-x264-params", "colormatrix=bt709", "-c:a", "copy", str(output_file)]
        elif encoder == 2: # GPU (CUDA)
            args = ["-y", "-hwaccel", "cuda", "-i", str(mkv_path), "-fps_mode", "passthrough", "-vf", subs, "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", "-b:v", f"{task.gpu_bitrate}M", "-bufsize", "15M", "-maxrate", "15M", "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20", "-i_qfactor", "0.75", "-b_qfactor", "1.1", str(output_file)]
        elif encoder == 3: # GPU (VA-API)
            args = ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi", "-i", str(mkv_path), "-vf", f"{subs},format=nv12,hwupload", "-c:a", "copy", "-c:v", "h264_vaapi", "-b:v", f"{task.gpu_bitrate}M", str(output_file)]
        elif encoder == 4: # GPU (VA-API AV1)
            args = ["-hwaccel", "vaapi", "-hwaccel_output_format", "vaapi", "-i", str(mkv_path), "-vf", f"{subs},format=nv12,hwupload", "-c:a", "copy", "-c:v", "av1_vaapi", "-b:v", f"{task.gpu_bitrate}M", str(output_file)]
        else:
            return None
        return "ffmpeg", args

    def _subtitles_filter(self, task, mkv_path):
        """Filtr subtitles dla hardsubu.
        Skrypt 1: zewnętrzne napisy, jeśli podane (inaczej osadzone w MKV) + opcjonalny folder czcionek.
        Uwaga: przy zewnętrznych napisach FFmpeg NIE widzi czcionek z załączników MKV - tylko fontsdir i system.
        Skrypt 2 (legacy): zawsze napisy z remuxu, bez zmian."""
        source = mkv_path
        fonts = None
        if task.selected_script == 1:
            if task.subtitle_file:
                source = task.subtitle_file
            if task.font_folder:
                fonts = task.font_folder
        flt = f"subtitles='{self._get_safe_path_for_ffmpeg(source)}'"
        if fonts:
            flt += f":fontsdir='{self._get_safe_path_for_ffmpeg(fonts)}'"
        return flt

    def _build_ffmpeg_intro(self, task, framerate=None):
        """Zwraca (program, args) albo None, jeśli enkoder jest niepoprawny."""
        mkv_path, intro_path = Path(task.mkv_file), Path(task.intro_file)

        if task.output_path:
            output_file = task.output_path
        else:
            output_file = mkv_path.with_name(f"{mkv_path.stem}_HARD.mp4")

        subtitle_path = self._get_safe_path_for_ffmpeg(mkv_path)
        bitrate = task.gpu_bitrate
        framerate_arg = ["-r:v", framerate] if framerate else []

        # loudnorm wewnętrznie pracuje na 192 kHz i (od FFmpeg 8.1.x/9.0) w filter_complex psuje PTS.
        # Jawne ujednolicenie formatu + przeliczenie znaczników czasu sprawia, że concat działa
        # identycznie na każdej wersji FFmpeg. Siła normalizacji bez zmian.
        audio_post = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=N/SR/TB"
        audio_filter = (
            f"[0:a:0]loudnorm=I=-20:LRA=10:tp=-1.8,{audio_post}[a_intro_norm];"
            f"[1:a:0]loudnorm=I=-20:LRA=10:tp=-1.8,{audio_post}[a_main_norm];"
            "[a_intro_norm][a_main_norm]concat=n=2:v=0:a=1[a_out]"
        )

        encoder = task.selected_ffmpeg_script

        # Skrypt dla CPU
        if encoder == 1:
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
            return "ffmpeg", args

        # Skrypty dla GPU (CUDA lub VA-API)
        if encoder in [2, 3, 4]:
            video_filter_cpu = f"[1:v]subtitles='{subtitle_path}'[v_subs];[0:v][v_subs]concat=n=2:v=1:a=0[v_cpu]"

            if encoder == 2:
                hw_accel_args = ["-init_hw_device", "cuda=cu:0",
                                 "-filter_hw_device", "cu",
                                 "-hwaccel", "cuda"]
                filter_complex = f"{video_filter_cpu};[v_cpu]hwupload_cuda[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "h264_nvenc", "-preset", "p2"]
            elif encoder == 3:
                hw_accel_args = ["-init_hw_device", f"vaapi=va:{self.vaapi_device}",
                                 "-filter_hw_device", "va",
                                 "-hwaccel", "vaapi"]
                filter_complex = f"{video_filter_cpu};[v_cpu]format=nv12,hwupload[v_out];{audio_filter}"
                video_codec_args = ["-c:v", "h264_vaapi", "-profile:v", "high"]
            else:
                hw_accel_args = ["-init_hw_device", f"vaapi=va:{self.vaapi_device}",
                                 "-filter_hw_device", "va",
                                 "-hwaccel", "vaapi"]
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
            return "ffmpeg", args

        return None

    @staticmethod
    def _probe_framerate_sync(mkv_file):
        """Synchroniczny ffprobe na potrzeby podglądu (prawdziwe uruchomienie używa wersji async)."""
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                 '-show_entries', 'stream=r_frame_rate', '-of', 'json', str(mkv_file)],
                capture_output=True, text=True, timeout=15)
            streams = json.loads(result.stdout or "{}").get('streams', [])
            return streams[0].get('r_frame_rate') if streams else None
        except Exception:
            return None

    def build_command_preview(self, task):
        """Lista (opis_kroku, komenda_tekst) dla zadania - dokładnie to, co uruchomi kolejka."""
        missing = self._missing_inputs(task)
        if missing:
            return [("BŁĄD", f"Zadanie nie zostanie uruchomione - brak: {', '.join(missing)}")]

        steps = []
        script = task.selected_script
        if script == 1:
            steps.append(("FFmpeg (hardsub)", self._build_ffmpeg(task, task.mkv_file)))
        elif script == 2:
            remux = self._remux_output_path(task.mkv_file)
            steps.append(("Krok 1/2: mkvmerge", self._build_mkvmerge(task, remux)))
            steps.append(("Krok 2/2: FFmpeg (hardsub)", self._build_ffmpeg(task, remux, is_final=True)))
        elif script == 3:
            output = task.output_path or self._remux_output_path(task.mkv_file)
            steps.append(("mkvmerge (remux)", self._build_mkvmerge(task, output)))
        elif script == 4:
            framerate = self._probe_framerate_sync(task.mkv_file)
            label = "FFmpeg + wstawka" + ("" if framerate else " (UWAGA: ffprobe nie odczytał framerate - brak -r:v)")
            steps.append((label, self._build_ffmpeg_intro(task, framerate)))
        else:
            return [("BŁĄD", f"Nieznany typ skryptu: {script}")]

        return [(label, self.format_command(*cmd) if cmd else "BŁĄD: niepoprawny enkoder FFmpeg - komenda nie powstanie")
                for label, cmd in steps]

    def _launch(self, program, args, status):
        """Wspólne uruchomienie: log komendy + start procesu."""
        command_text = self.format_command(program, args)
        if self.debug_mode:
            self.log_debug(f"Running command: {command_text}")
        self.task_manager.mark_current_as_processing(status)
        self._start_process(program, args)   # czyści okno logu
        if self.debug_mode:
            self.output_window.append(f">>> Uruchomiona komenda:\n{command_text}\n")

    # ------------------------------------------------------------------
    # Uruchamianie
    # ------------------------------------------------------------------

    def run_mkvmerge(self, mkv_file, subtitle_file, font_folder):
        task = self.current_task
        output_file = task.output_path or self._remux_output_path(mkv_file)
        program, args = self._build_mkvmerge(task, output_file)
        self._launch(program, args, "Uruchomiono mkvmerge")

    def run_mkvmerge_ffmpeg(self, mkv_file, subtitle_file, font_folder):
        output_file_remux = self._remux_output_path(mkv_file)
        self.chained_command_info = {'function': self.run_ffmpeg, 'args': (output_file_remux, True)}
        program, args = self._build_mkvmerge(self.current_task, output_file_remux)
        self._launch(program, args, "Krok 1/2: Uruchomiono mkvmerge")

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
        if self._probing:
            return True
        return self.process is not None and self.process.state() == QProcess.ProcessState.Running

    @staticmethod
    def _detect_vaapi_device():
        try:
            nodes = sorted(Path("/dev/dri").glob("renderD*"))
            if nodes:
                return str(nodes[0])
        except Exception:
            pass
        return "/dev/dri/renderD128"

    def _get_safe_path_for_ffmpeg(self, file_path):
        # Konwersja na ciąg znaków
        path_str = str(file_path)
        
        # FFmpeg parsuje ścieżkę w filtrze dwa razy, więc escape'ujemy na dwóch poziomach.
        # Wynik jest wstawiany jako subtitles='<wynik>'.
        # Poziom 1 (wartość opcji filtra): backslash, apostrof i dwukropek poprzedzamy backslashem.
        path_str = ''.join('\\' + c if c in "\\':" else c for c in path_str)
        # Poziom 2 (graf filtrów, wewnątrz '...'): tam wszystko jest dosłowne poza apostrofem,
        # który trzeba zapisać jako '\'' (zamknij cudzysłów, wstaw \', otwórz ponownie).
        # Stara wersja używała tu samego \', co psuło każdy plik z apostrofem w nazwie.
        return path_str.replace("'", "'\\''")

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
        cmd = self._build_ffmpeg(self.current_task, mkv_file, is_final)
        if not cmd:
            self.log_message.emit("BŁĄD: Nie wybrano poprawnego enkodera FFmpeg.")
            self.task_completed(success=False)
            return
        status = "Krok 2/2: Uruchomiono FFmpeg" if is_final else "Uruchomiono FFmpeg"
        self._launch(*cmd, status)

    def run_ffmpeg_with_intro(self, mkv_file, intro_file):
        self.log_terminal("run_ffmpeg_with_intro called.")
        # Użyj framerate pobranego wcześniej asynchronicznie
        framerate = getattr(self, '_current_task_framerate', None)
        cmd = self._build_ffmpeg_intro(self.current_task, framerate)
        if not cmd:
            # Wcześniej tu był cichy return, który zawieszał kolejkę.
            self.log_message.emit("BŁĄD: Nie wybrano poprawnego enkodera FFmpeg.")
            self.task_completed(success=False)
            return
        self.log_terminal(f"Final args list: {cmd[1]}")
        self._launch(*cmd, "Uruchomiono FFmpeg z wstawką")

    def log_debug(self, message):
        if not self.debug_mode:
            return
        with open(self.log_file_path, "a", encoding='utf-8') as log_file:
            log_file.write(f"{datetime.now()}: {message}\n")

    def log_terminal(self, message):
        if self.debug_mode:
            print(f"DEBUG: {message}")

