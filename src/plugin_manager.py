import sys
import json
import base64 # <-- NOWY IMPORT
from pathlib import Path
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import QApplication # <-- NOWY IMPORT

class PluginManager:
    """
    Zarządza wykrywaniem, ładowaniem i uruchamianiem dodatków (DLC).
    """
    def __init__(self, parent_window):
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent

        self.dlc_folder = base_path / 'DLC'
        self.parent = parent_window
        self.plugins = []
        self.processes = []

    def scan_for_plugins(self):
        """
        Skanuje folder 'DLC' w poszukiwaniu prawidłowych dodatków.
        """
        self.plugins.clear()
        if not self.dlc_folder.exists() or not self.dlc_folder.is_dir():
            print(f"Folder DLC nie istnieje: {self.dlc_folder}")
            return

        for item in self.dlc_folder.iterdir():
            if item.is_dir():
                manifest_path = item / 'plugin.json'
                if manifest_path.is_file():
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        required_keys = ['name', 'author', 'version', 'description', 'executable']
                        if all(key in data for key in required_keys):
                            plugin_info = {
                                'name': data['name'], 'author': data['author'],
                                'version': data['version'], 'description': data['description'],
                                'executable': data['executable'], 'path': item
                            }
                            self.plugins.append(plugin_info)
                        else:
                            print(f"Błąd wczytywania dodatku z {item}: brak wymaganych kluczy w plugin.json.")
                    except Exception as e:
                        print(f"Nieoczekiwany błąd podczas wczytywania dodatku z {item}: {e}")

    def get_plugins(self):
        """Zwraca listę wykrytych, poprawnych dodatków."""
        return self.plugins

    def launch_plugin(self, plugin_info):
        """
        Uruchamia wybrany dodatek jako osobny proces i podłącza mechanizm czyszczący.
        """
        executable_path = plugin_info['path'] / plugin_info['executable']

        if not executable_path.is_file():
            print(f"Błąd: Plik wykonywalny '{executable_path}' dla dodatku '{plugin_info['name']}' nie istnieje.")
            return

        app = QApplication.instance()
        current_style_name = app.style().objectName()
        stylesheet = app.styleSheet()
        style_to_pass = 'Fusion' if stylesheet else current_style_name

        args = [str(executable_path), '--style-name', style_to_pass]
        if stylesheet:
            encoded_stylesheet = base64.b64encode(stylesheet.encode('utf-8')).decode('utf-8')
            args.extend(['--stylesheet-b64', encoded_stylesheet])

        process = QProcess(self.parent)

        # --- KLUCZOWA ZMIANA ---
        # Po zakończeniu procesu (normalnie lub przez błąd), uruchom metodę czyszczącą.
        process.finished.connect(lambda: self.cleanup_process(process))
        # ---------------------

        process.start(sys.executable, args)
        self.processes.append(process)

    def cleanup_process(self, process):
        """
        Usuwa referencję do zakończonego procesu z listy, aby zwolnić pamięć.
        """
        if process in self.processes:
            self.processes.remove(process)
            print("Oczyszczono zakończony proces dodatku.") # Opcjonalny log
