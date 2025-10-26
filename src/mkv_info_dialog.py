import json
import subprocess
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QApplication, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class MkvInfoWorker(QThread):
    """Wątek do odczytywania informacji o pliku MKV w tle."""
    info_ready = pyqtSignal(str)

    def __init__(self, mkv_path):
        super().__init__()
        self.mkv_path = mkv_path

    def _format_bitrate(self, bitrate_str):
        """Inteligentnie formatuje bitrate do kbps lub Mbps."""
        try:
            bitrate = int(bitrate_str)
            if bitrate == 0:
                return "Brak danych"
            kbps = bitrate / 1000
            if kbps < 1000:
                return f"{kbps:.0f} kbps"
            else:
                mbps = kbps / 1000
                return f"{mbps:.2f} Mbps"
        except (ValueError, TypeError):
            return "Brak danych"

    def run(self):
        try:
            command = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_streams", "-show_format", str(self.mkv_path)
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
            data = json.loads(result.stdout)

            output_lines = [f"<h3>{self.mkv_path.name}</h3>"]

            format_info = data.get('format', {})
            duration_sec = float(format_info.get('duration', 0))
            size_mb = float(format_info.get('size', 0)) / (1024 * 1024)
            total_bitrate = self._format_bitrate(format_info.get('bit_rate'))

            h, m, s = int(duration_sec / 3600), int((duration_sec % 3600) / 60), int(duration_sec % 60)

            output_lines.append("<b>Informacje ogólne:</b>")
            output_lines.append(f"&nbsp;&nbsp;Rozmiar: {size_mb:.2f} MB")
            output_lines.append(f"&nbsp;&nbsp;Czas trwania: {h:02d}:{m:02d}:{s:02d}")
            output_lines.append(f"&nbsp;&nbsp;Całkowity bitrate: {total_bitrate}")
            output_lines.append("<hr>")

            output_lines.append("<b>Ścieżki w pliku:</b>")
            for stream in data.get('streams', []):
                codec_type = stream.get('codec_type', 'nieznany')

                # --- KLUCZOWA POPRAWKA: IGNORUJEMY ZAŁĄCZNIKI ---
                if codec_type == 'attachment':
                    continue

                stream_index = stream.get('index', 'N/A')
                codec_name = stream.get('codec_name', 'N/A').upper()
                lang = stream.get('tags', {}).get('language', 'brak')
                title = stream.get('tags', {}).get('title', '')

                line = f"&nbsp;&nbsp;<b>{stream_index}: {codec_type.capitalize()}</b> ({codec_name}, Język: {lang})"
                if title:
                    line += f" - <i>{title}</i>"
                output_lines.append(line)

                if codec_type == 'video':
                    width = stream.get('width', 'N/A')
                    height = stream.get('height', 'N/A')
                    fps_raw = stream.get('r_frame_rate', '0/1')
                    try:
                        num, den = map(int, fps_raw.split('/'))
                        fps = num / den if den > 0 else 0
                        fps_str = f"{fps:.3f} FPS ({fps_raw})"
                    except Exception:
                        fps_str = fps_raw

                    # --- POPRAWKA: DODANO BITRATE WIDEO ---
                    video_bitrate = self._format_bitrate(stream.get('bit_rate'))

                    output_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;Rozdzielczość: {width}x{height}")
                    output_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;Klatkaż: {fps_str}")
                    output_lines.append(f"&nbsp;&nbsp;&nbsp;&nbsp;Bitrate wideo: {video_bitrate}")

            self.info_ready.emit("<br>".join(output_lines))

        except (subprocess.CalledProcessError, FileNotFoundError):
            self.info_ready.emit("<b>Błąd:</b> Nie można uruchomić ffprobe.")
        except Exception as e:
            self.info_ready.emit(f"<b>Błąd odczytu informacji:</b><br>{e}")


class MkvInfoDialog(QDialog):
    """Okno dialogowe wyświetlające szczegółowe informacje o pliku MKV."""
    def __init__(self, mkv_file_path, parent=None):
        super().__init__(parent)
        self.mkv_file_path = mkv_file_path

        self.setWindowTitle("Informacje o pliku")
        self.resize(550, 400) # Ustawienie domyślnego, ale elastycznego rozmiaru
        self.setStyleSheet(QApplication.instance().styleSheet())

        layout = QVBoxLayout(self)

        # Etykieta z informacjami
        self.info_label = QLabel("Wczytywanie informacji...")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.info_label.setWordWrap(True)
        self.info_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # Panel przewijania
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.info_label)
        scroll_area.setStyleSheet("background: transparent; border: none;") # Dopasowanie do tła
        layout.addWidget(scroll_area)

        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.start_worker()

    def start_worker(self):
        self.worker = MkvInfoWorker(self.mkv_file_path)
        self.worker.info_ready.connect(self.update_info)
        self.worker.start()

    def update_info(self, info_html):
        self.info_label.setText(info_html)
