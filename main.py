import pystray
from PIL import Image, ImageDraw
import threading
import time
import os

import datetime
from config import load_config
from recorder import AudioRecorder
from transcriber import transcribe_audio
from settings_gui import open_settings

class MeetingAssistantApp:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.is_recording = False
        self.is_processing = False
        self.icon = None

    def create_image(self, color):
        # Generate a simple 64x64 icon
        image = Image.new('RGB', (64, 64), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((16, 16, 48, 48), fill=color)
        return image

    def update_icon(self, state):
        if not self.icon: return
        
        if state == "idle":
            self.icon.icon = self.create_image('black')
            self.icon.title = "Meeting Assistant - Idle"
        elif state == "recording":
            self.icon.icon = self.create_image('red')
            self.icon.title = "Meeting Assistant - Recording"
        elif state == "processing":
            self.icon.icon = self.create_image('yellow')
            self.icon.title = "Meeting Assistant - Processing"

    def process_recording(self, audio_file):
        self.update_icon("processing")
        
        try:
            config = load_config()
            out_folder = config.get("output_folder") or os.getcwd()
            os.makedirs(out_folder, exist_ok=True)
            
            now = datetime.datetime.now()
            filename = now.strftime("meeting_%Y-%m-%d_%H-%M-%S.md")
            output_txt = os.path.join(out_folder, filename)
            
            print("Транскрибування...")
            transcript_file = transcribe_audio(audio_file, model_size="small", output_txt=output_txt)
            
            if transcript_file:
                print(f"Транскрипт готовий: {transcript_file}")
                
        except Exception as e:
            print(f"Помилка під час обробки: {e}")
            
        self.is_processing = False
        self.update_icon("idle")
        print("Готово. Очікування...")

    def toggle_record(self, icon, item):
        if self.is_processing:
            return # Block if already processing
            
        if not self.is_recording:
            # Start
            self.is_recording = True
            self.update_icon("recording")
            self.recorder.start_recording()
        else:
            # Stop
            self.is_recording = False
            
            audio_path = os.path.join(os.getcwd(), "meeting_record.wav")
            audio_file = self.recorder.stop_recording(audio_path)
            
            if audio_file:
                self.is_processing = True
                # Run heavy processing in background thread
                threading.Thread(target=self.process_recording, args=(audio_file,), daemon=True).start()
            else:
                self.update_icon("idle")

    def open_settings_window(self, icon, item):
        import subprocess
        import sys
        # Run settings GUI in a separate process to avoid Tkinter threading bugs
        # Using sys.executable allows this to work correctly when compiled as a .exe
        subprocess.Popen([sys.executable, "--settings"])

    def exit_app(self, icon, item):
        if self.is_recording:
            self.recorder.stop_recording()
        self.recorder.terminate()
        icon.stop()

    def run(self):
        menu = pystray.Menu(
            pystray.MenuItem('Start / Stop Recording', self.toggle_record),
            pystray.MenuItem('Settings', self.open_settings_window),
            pystray.MenuItem('Exit', self.exit_app)
        )
        
        self.icon = pystray.Icon("MeetingAssistant", self.create_image('black'), "Meeting Assistant", menu)
        print("Meeting Assistant запущено. Знайдіть іконку в треї (чорне коло).")
        self.icon.run()

if __name__ == "__main__":
    import sys
    
    # Check if we are being launched as the settings GUI process
    if len(sys.argv) > 1 and sys.argv[1] == "--settings":
        open_settings()
        sys.exit(0)
        
    app = MeetingAssistantApp()
    app.run()
