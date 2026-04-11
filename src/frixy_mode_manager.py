# frixy_mode_manager.py
import json
import ssl
import urllib.request
import re
import os
from datetime import datetime

class FrixyModeManager:
    _instance = None
    _data = None
    _local_file = "frixy_series_cache.json"

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FrixyModeManager()
        return cls._instance

    def fetch_data(self, url, force=False):
        # 1. Jeśli wymuszono odświeżenie, pobierz z sieci
        if force:
            return self._fetch_from_network(url)
            
        # 2. Jeśli mamy już w pamięci, zwróć
        if self._data is not None:
            return self._data
            
        # 3. Spróbuj wczytać z pliku lokalnego
        if os.path.exists(self._local_file):
            try:
                with open(self._local_file, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                return self._data
            except Exception as e:
                print(f"Błąd wczytywania cache Frixy: {e}")

        # 4. Jeśli nie ma cache, pobierz z sieci
        return self._fetch_from_network(url)

    def _fetch_from_network(self, url):
        try:
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(url, context=context) as response:
                data = json.loads(response.read().decode())
                if "years" in data:
                    self._data = data["years"]
                else:
                    self._data = data
                
                # Zapisz do cache lokalnego
                try:
                    with open(self._local_file, "w", encoding="utf-8") as f:
                        json.dump(self._data, f, indent=4, ensure_ascii=False)
                except Exception as e:
                    print(f"Błąd zapisu cache Frixy: {e}")
                    
                return self._data
        except Exception as e:
            print(f"Błąd pobierania bazy Frixy z sieci: {e}")
            return self._data if self._data else {}

    def get_current_season_year(self):
        now = datetime.now()
        y, m = str(now.year), now.month
        if 1 <= m <= 3: s = "Zima"
        elif 4 <= m <= 6: s = "Wiosna"
        elif 7 <= m <= 9: s = "Lato"
        else: s = "Jesień"
        return y, s

    def parse_source_filename(self, filename):
        fn = filename.upper()
        # Wyciąganie odcinka: S01E01, - 01, (01), 01
        ep_match = re.search(r'[S\d]+E(\d+)', fn) or re.search(r' - (\d+)', fn) or re.search(r'\((\d+)\)', fn) or re.search(r'(\d+)', fn)
        ep = ep_match.group(1) if ep_match else "01"
        
        meta = {"res": "1080p", "source": "WEB-DL", "v_codec": "H.264", "a_codec": "AAC", "ep": ep}
        
        if "2160P" in fn or "4K" in fn: meta["res"] = "2160p"
        elif "1080P" in fn: meta["res"] = "1080p"
        elif "720P" in fn: meta["res"] = "720p"
        
        if "CR" in fn or "CRUNCHY" in fn: meta["source"] = "CR WEB-DL"
        elif "AMZN" in fn or "AMAZON" in fn: meta["source"] = "AMZN WEB-DL"
        elif "HIDIVE" in fn: meta["source"] = "HIDIVE WEB-DL"
        elif "NF" in fn or "NETFLIX" in fn: meta["source"] = "NF WEB-DL"
        elif "WEB-RIP" in fn or "WEBRIP" in fn: meta["source"] = "WEB-Rip"
        elif "BLURAY" in fn or "BD" in fn: meta["source"] = "BD"
        
        if "HEVC" in fn or "X265" in fn or "H265" in fn: meta["v_codec"] = "HEVC"
        
        if "FLAC" in fn: meta["a_codec"] = "FLAC"
        elif "E-AC-3" in fn or "EAC3" in fn: meta["a_codec"] = "E-AC-3"
        elif "OPUS" in fn: meta["a_codec"] = "OPUS"
        
        return meta

    def generate_output_name(self, series_data, episode_number, tags, script_id):
        if not series_data:
            return ""
            
        nf = series_data.get('naming_title', series_data.get('title', 'Unknown')) if isinstance(series_data, dict) else series_data
        ep_val = str(episode_number).zfill(2)
        season_val = series_data.get('season_number', 1) if isinstance(series_data, dict) else 1
        season_str = f"S{str(season_val).zfill(2)}"
        
        abs_start = series_data.get('absolute_episode_start', 0) if isinstance(series_data, dict) else 0
        abs_str = ""
        if abs_start > 0 and episode_number.isdigit():
            abs_str = f" ({abs_start + int(episode_number) - 1})"
            
        is_encode = script_id in [1, 4]
        ext = "mp4" if is_encode else "mkv"
        suffix = " [HARD]" if is_encode else ""
        
        return f"[FrixySubs] {nf} - {season_str}E{ep_val}{abs_str} [{tags['res']} {tags['source']} {tags['v_codec']} {tags['a_codec']}] [Napisy PL]{suffix}.{ext}"
