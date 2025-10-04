# discord_rpc_manager.py
import time
import logging
import os
import platform  # Importujemy moduł platform
from threading import Thread

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def find_discord_pipe():
    # --- POPRAWKA DLA WINDOWS ---
    # Jeśli system to nie Linux/macOS, zwracamy 0, pypresence poradzi sobie samo.
    if platform.system() == 'Windows':
        return 0

    # Kod specyficzny dla Linuksa
    uid = os.getuid()
    possible_paths = {
        'native': f'/run/user/{uid}/discord-ipc-{{}}',
        'flatpak': f'/run/user/{uid}/app/com.discordapp.Discord/discord-ipc-{{}}'
    }
    for i in range(10):
        for path_template in possible_paths.values():
            path = path_template.format(i)
            if os.path.exists(path):
                return i
    return None

class DiscordRPCManager:
    def __init__(self, app_id):
        self.app_id = app_id
        self.task_manager = None
        self.thread = None
        self._stop_flag = False
        self.lib_available = False
        try:
            from pypresence import Presence, exceptions
            self.pypresence_lib = Presence
            self.pypresence_exceptions = exceptions
            self.lib_available = True
        except ImportError:
            logger.warning("Biblioteka pypresence nie jest zainstalowana.")

    def start(self):
        if not self.lib_available or (self.thread and self.thread.is_alive()):
            return
        self._stop_flag = False
        self.thread = Thread(target=self._run_rpc_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not (self.thread and self.thread.is_alive()):
            return
        self._stop_flag = True
        self.thread.join(timeout=2.0)

    def _run_rpc_loop(self):
        presence = None
        while not self._stop_flag:
            try:
                pipe_number = find_discord_pipe()
                # Na Linuksie, jeśli nie znajdziemy pipe, czekamy. Na Windows (gdzie pipe_number=0) pypresence samo rzuci błędem.
                if pipe_number is None and platform.system() != 'Windows':
                    logger.warning("Nie znaleziono Discorda. Ponowna próba za 30s.")
                    time.sleep(30)
                    continue

                presence = self.pypresence_lib(self.app_id, pipe=pipe_number)
                presence.connect()

                session_start_time = int(time.time())
                logger.info("Połączono z Discord RPC.")

                while not self._stop_flag:
                    self.update_presence(presence, session_start_time)
                    is_ffmpeg_running = self.task_manager and self.task_manager.process_manager.is_running()
                    update_interval = 3 if is_ffmpeg_running else 15
                    time.sleep(update_interval)

            except self.pypresence_exceptions.DiscordNotFound:
                 logger.warning("Nie znaleziono uruchomionej aplikacji Discord. Ponowna próba za 30s.")
                 time.sleep(30)
            except Exception as e:
                logger.error(f"Błąd w pętli RPC: {e}")
            finally:
                if presence:
                    try:
                        presence.close()
                    except Exception:
                        pass
                presence = None
                if not self._stop_flag:
                    time.sleep(15)

    def update_presence(self, presence, start_time):
        if not self.task_manager:
            return
        is_processing = self.task_manager.process_manager.is_running()
        tasks = self.task_manager.tasks
        num_tasks = len(tasks)
        details, state = "Oczekuje na zadania", "Brak zadań w kolejce"
        script_to_details_map = {1: "Przetwarza: Hardsuba", 2: "Przetwarza: Remuxa + Hardsuba", 3: "Przetwarza: Remuxa", 4: "Przetwarza: Hardsuba z intrem"}
        if num_tasks > 0:
            current_task = self.task_manager.get_task(0)
            if is_processing:
                details = script_to_details_map.get(current_task.selected_script, "Przetwarza...")
                ffmpeg_speed = self.task_manager.process_manager.current_ffmpeg_speed
                if current_task.selected_script in [1, 2, 4] and ffmpeg_speed:
                    state = f"Prędkość: {ffmpeg_speed}"
                else:
                    state = f"{num_tasks - 1} w kolejce" if num_tasks > 1 else "Ostatnie zadanie"
            else:
                details = "Oczekuje na rozpoczęcie..."
                state = f"{num_tasks} zadań w kolejce"
        payload = {'details': details, 'state': state, 'large_image': "automatyzer_logo_512", 'large_text': "Automatyzer by kacper12gry"}
        if start_time:
            payload['start'] = start_time
        try:
            presence.update(**payload)
        except Exception:
            pass
