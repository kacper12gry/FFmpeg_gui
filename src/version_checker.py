import urllib.request
import json
from PyQt6.QtCore import QThread, pyqtSignal

class VersionChecker(QThread):
    """Wątek do sprawdzania najnowszej wersji na GitHubie w tle."""
    check_complete = pyqtSignal(str, str) # Sygnał emitujący (tag_name, release_url)
    error_occurred = pyqtSignal(str)

    API_URL = "https://api.github.com/repos/kacper12gry/FFmpeg_gui/releases/latest"

    def run(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/vnd.github.v3+json'
            }
            req = urllib.request.Request(self.API_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get("tag_name")
                release_url = data.get("html_url")

                if latest_version and release_url:
                    self.check_complete.emit(latest_version, release_url)
                else:
                    self.error_occurred.emit("Nie znaleziono tag_name lub html_url w odpowiedzi API.")

        except Exception as e:
            self.error_occurred.emit(f"Błąd połączenia z GitHub API: {e}")
