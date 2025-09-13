import os
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
        Uruchamia wybrany dodatek jako osobny proces, inteligentnie przekazując
        informacje o motywie.
        """
        executable_path = plugin_info['path'] / plugin_info['executable']

        if not executable_path.is_file():
            print(f"Błąd: Plik wykonywalny '{executable_path}' dla dodatku '{plugin_info['name']}' nie istnieje.")
            return

        app = QApplication.instance()

        # --- KLUCZOWA ZMIANA: Inteligentne określanie stylu ---

        # Pobierz aktualny styl i arkusz stylów z głównej aplikacji
        current_style_name = app.style().objectName()
        stylesheet = app.styleSheet()

        # Domyślnie przekazujemy to, co jest w aplikacji głównej
        style_to_pass = current_style_name

        # Jeśli arkusz stylów jest pusty, to znaczy, że używamy motywu systemowego.
        # Jeśli jednak nie jest pusty, to znaczy, że mamy motyw "Ciemny" lub "Jasny",
        # które wymagają stylu "Fusion" do poprawnego działania.
        if stylesheet:
            style_to_pass = 'Fusion'

        # Przygotuj argumenty do przekazania
        args = [str(executable_path)]
        args.extend(['--style-name', style_to_pass])

        if stylesheet:
            encoded_stylesheet = base64.b64encode(stylesheet.encode('utf-8')).decode('utf-8')
            args.extend(['--stylesheet-b64', encoded_stylesheet])

        # Uruchom proces z dodatkowymi argumentami
        process = QProcess(self.parent)
        process.start(sys.executable, args)
        self.processes.append(process)
