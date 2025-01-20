import os
from PyQt5.QtCore import QProcess

class ProcessManager:
    def __init__(self, queue, output_window, task_list):
        self.queue = queue
        self.output_window = output_window
        self.task_list = task_list
        self.process = None
        self.selected_script = 1  # Default to the first script
        self.gpu_bitrate = 8  # Default bitrate for GPU script in Mbps

    def is_running(self):
        return self.process and self.process.state() == QProcess.Running

    def kill_process(self):
        if self.process:
            self.process.kill()

    def process_next_in_queue(self):
        if not self.queue.empty():
            mkv_file, subtitle_file, font_folder, selected_script, gpu_bitrate = self.queue.get()
            self.selected_script = selected_script
            self.gpu_bitrate = gpu_bitrate
            self.run_mkvmerge(mkv_file, subtitle_file, font_folder)

    def run_mkvmerge(self, mkv_file, subtitle_file, font_folder):
        final_output_file = mkv_file.replace(".mkv", "_final_output.mkv")
        font_files = ' '.join([f'--attach-file "{os.path.join(font_folder, font)}"' for font in os.listdir(font_folder) if font.endswith(('.ttf', '.otf', '.woff', '.woff2'))])
        command = f'mkvmerge -o "{final_output_file}" --no-subtitles --no-buttons --no-track-tags --no-chapters --no-attachments "{mkv_file}" --language 0:pol --track-name 0:"FrixySubs" "{subtitle_file}" --attachment-mime-type application/x-truetype-font {font_files}'
        self.output_window.clear()  # Clear the output window before starting a new process
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(lambda: self.run_ffmpeg(final_output_file))
        self.process.start(command)
        self.task_list.setCurrentRow(0)
        self.task_list.currentItem().setText(f"Wideo: {mkv_file}, Napisy: {subtitle_file}, Czcionki: {font_folder} (mkvmerge)")

    def run_ffmpeg(self, mkv_file):
        output_file = mkv_file.replace("_final_output.mkv", "_output.mp4")
        if self.selected_script == 1:
            command = [
                "ffmpeg", "-i", f'"{mkv_file}"', "-vf", f'format=yuv420p,subtitles=\'{mkv_file}\'',
                "-map_metadata", "-1", "-movflags", "faststart", "-c:v", "libx264", "-profile:v", "main",
                "-level:v", "4.0", "-preset", "veryfast", "-crf", "16", "-maxrate", "20M", "-bufsize", "25M",
                "-x264-params", "colormatrix=bt709", "-c:a", "copy", f'"{output_file}"'
            ]
        else:
            command = [
                "ffmpeg", "-y", "-vsync", "0", "-hwaccel", "cuda", "-i", f'"{mkv_file}"', "-vf", f'subtitles=\'{mkv_file}\'',
                "-c:a", "copy", "-c:v", "h264_nvenc", "-preset", "p2", "-tune", "1", f'-b:v {self.gpu_bitrate}M', "-bufsize", "15M", "-maxrate", "15M",
                "-qmin", "0", "-g", "250", "-bf", "3", "-b_ref_mode", "middle", "-temporal-aq", "1", "-rc-lookahead", "20",
                "-i_qfactor", "0.75", "-b_qfactor", "1.1", f'"{output_file}"'
            ]
        self.process = QProcess()
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyRead.connect(self.update_output)
        self.process.finished.connect(self.process_next_in_queue)
        self.process.finished.connect(self.mark_task_as_done)
        self.process.start(" ".join(command))
        self.task_list.setCurrentRow(0)
        self.task_list.currentItem().setText(f"Wideo: {mkv_file} (ffmpeg) - Skrypt: {'CPU' if self.selected_script == 1 else f'GPU (Nvidia) - Bitrate: {self.gpu_bitrate}M'}")

    def mark_task_as_done(self):
        # Usuń ukończone zadanie z listy
        self.task_list.takeItem(0)
        # Start the next task in the queue
        self.process_next_in_queue()

    def update_output(self):
        output = self.process.readAll().data().decode()
        self.output_window.append(output)
