# Automatyzer

Graficzna nakładka na FFmpeg i MKVToolNix do przygotowywania odcinków z napisami.

## Główne funkcje
- Remuxowanie kontenerów wideo (dołączanie napisów i czcionek przez mkvmerge).
- Wypalanie napisów (hardsub) – osadzonych w MKV lub z zewnętrznego pliku `.ass` z folderem czcionek.
- Doklejanie wstawki (intro) z normalizacją głośności.
- Kolejka zadań z importem z pliku TXT, presetami i podglądem postępu.
- Kodowanie na CPU lub GPU (NVIDIA CUDA, Intel/AMD VA-API, w tym AV1 przez VA-API).

## Instalacja / Uruchomienie (Plik ZIP)

Zależność:
```bash
pip install PyQt6 packaging

```
Uruchomienie:
```bash
python3 main.py

```
**Linux:** w zależności od dystrybucji może być wymagane doinstalowanie dodatkowych bibliotek systemowych.

#### Ubuntu / Debian / Pop!_OS
```bash
sudo apt-get install libxcb-cursor0 libxcb-xinerama0 libxcb-randr0 libxcb-image0 libxcb-keysyms1 libxcb-render-util0 libxkbcommon-x11-0
```

#### Fedora / RHEL
```bash
sudo dnf install libxcb xcb-util-cursor xcb-util-image xcb-util-keysyms xcb-util-renderutil libxkbcommon-x11
```
#### Arch Linux / Manjaro
```bash
sudo pacman -Syu libxcb xcb-util xcb-util-image xcb-util-keysyms xcb-util-renderutil libxkbcommon-x11
```

## Wymagania
- Python 3.11+
- FFmpeg 5.1+ (zalecane 8.0.x; kodowanie AV1 przez VA-API wymaga 6.0+)
- MKVToolNix

