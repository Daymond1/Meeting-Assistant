import tkinter as tk
from tkinter import ttk, filedialog
import os
import sys
import time
import datetime
import threading
import logging
import pystray
from PIL import Image, ImageDraw
import pyaudiowpatch as pyaudio

from config import load_config, save_config, get_log_filepath, get_app_dir
from recorder import AudioRecorder
from transcriber import transcribe_audio

# Color constants for the dark themed UI
BG_COLOR = "#1e1e2e"
CARD_COLOR = "#181825"
TEXT_COLOR = "#cdd6f4"
DIM_COLOR = "#a6adc8"
ACCENT_COLOR = "#89b4fa"
REC_COLOR = "#f38ba8"
SUCCESS_COLOR = "#a6e3a1"
WARN_COLOR = "#f9e2af"
BTN_BG = "#313244"
BORDER_COLOR = "#45475a"

logger = logging.getLogger("MeetingAssistant")

class HoverButton(tk.Button):
    def __init__(self, master, active_bg=ACCENT_COLOR, active_fg="#11111b", **kw):
        super().__init__(master, **kw)
        self.default_bg = self.cget('bg')
        self.default_fg = self.cget('fg')
        self.active_bg = active_bg
        self.active_fg = active_fg
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if self.cget('state') != tk.DISABLED:
            self.configure(bg=self.active_bg, fg=self.active_fg)

    def on_leave(self, e):
        if self.cget('state') != tk.DISABLED:
            self.configure(bg=self.default_bg, fg=self.default_fg)


class MeetingAssistantDashboard:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.is_recording = False
        self.record_start_time = 0
        self.icon = None
        self.root = None
        self.active_jobs = {}  # Keeps track of all concurrent transcription jobs

        # Build main window
        self.setup_gui()
        


    def create_image(self, color):
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

    def show_notification(self, message, title="Meeting Assistant"):
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.error(f"Failed to show system notification: {e}")

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Meeting Assistant - Control Panel")
        self.root.geometry("520x630")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        # Style configurations for TTK elements
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TCombobox", fieldbackground="#11111b", background=BTN_BG, foreground=TEXT_COLOR, arrowcolor=ACCENT_COLOR, bordercolor=BORDER_COLOR)
        style.map("TCombobox", fieldbackground=[('readonly', "#11111b")], foreground=[('readonly', TEXT_COLOR)])
        
        # Configure horizontal progressbar style
        style.configure("Horizontal.TProgressbar", foreground=ACCENT_COLOR, background=ACCENT_COLOR, troughcolor="#11111b", bordercolor=BORDER_COLOR, thickness=6)
        
        # Intercept closing window to hide it to tray instead of exiting
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Start with the window hidden (as a background tray app)
        self.root.withdraw()

        # 1. Header Frame
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill=tk.X, padx=20, pady=(10, 5))
        
        logo_label = tk.Label(header_frame, text="🎙️ Meeting Assistant", bg=BG_COLOR, fg=ACCENT_COLOR, font=("Segoe UI", 15, "bold"))
        logo_label.pack(side=tk.LEFT)
        
        ver_label = tk.Label(header_frame, text="v1.3", bg=BG_COLOR, fg=DIM_COLOR, font=("Segoe UI", 8))
        ver_label.pack(side=tk.LEFT, padx=5, pady=(5, 0))

        # 2. Status Card Frame
        self.status_card = tk.Frame(self.root, bg=CARD_COLOR, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.status_card.pack(fill=tk.X, padx=20, pady=5)
        
        self.status_title = tk.Label(self.status_card, text="IDLE", bg=CARD_COLOR, fg=DIM_COLOR, font=("Segoe UI", 11, "bold"))
        self.status_title.pack(pady=(8, 2))
        
        self.timer_label = tk.Label(self.status_card, text="00:00:00", bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        self.timer_label.pack(pady=2)
        
        self.status_desc = tk.Label(self.status_card, text="Ready", bg=CARD_COLOR, fg=DIM_COLOR, font=("Segoe UI", 8, "italic"))
        self.status_desc.pack(pady=(2, 8))

        # 3. Main Action Button Frame
        actions_frame = tk.Frame(self.root, bg=BG_COLOR)
        actions_frame.pack(fill=tk.X, padx=20, pady=2)

        self.record_btn = HoverButton(
            actions_frame, 
            text="Start Recording ⏺️", 
            bg=SUCCESS_COLOR, 
            fg="#11111b",
            active_bg="#bbf7d0",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            bd=0,
            padx=20,
            pady=8,
            cursor="hand2",
            command=self.toggle_record
        )
        self.record_btn.pack(fill=tk.X, pady=2)

        # 4. Settings Card Frame (Always visible)
        self.settings_frame = tk.Frame(self.root, bg=CARD_COLOR, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.settings_frame.pack(fill=tk.X, padx=20, pady=5)

        self.load_device_lists()
        config = load_config()

        # Settings Contents
        tk.Label(self.settings_frame, text="Microphone:", bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=15, pady=4)
        self.mic_var = tk.StringVar()
        self.mic_combo = ttk.Combobox(self.settings_frame, textvariable=self.mic_var, width=42, state="readonly")
        mic_disp = [f"{idx}: {name}" for idx, name in self.mic_devices]
        self.mic_combo['values'] = ["Default"] + mic_disp
        self.mic_combo.set("Default")
        if config.get("mic_device_index") is not None:
            match = next((x for x in mic_disp if x.startswith(str(config["mic_device_index"]) + ":")), None)
            if match: self.mic_combo.set(match)
        self.mic_combo.grid(row=0, column=1, columnspan=2, padx=15, pady=4, sticky="ew")

        tk.Label(self.settings_frame, text="Speakers (System):", bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", padx=15, pady=4)
        self.spk_var = tk.StringVar()
        self.spk_combo = ttk.Combobox(self.settings_frame, textvariable=self.spk_var, width=42, state="readonly")
        spk_disp = [f"{idx}: {name}" for idx, name in self.spk_devices]
        self.spk_combo['values'] = ["Default"] + spk_disp
        self.spk_combo.set("Default")
        if config.get("speaker_device_index") is not None:
            match = next((x for x in spk_disp if x.startswith(str(config["speaker_device_index"]) + ":")), None)
            if match: self.spk_combo.set(match)
        self.spk_combo.grid(row=1, column=1, columnspan=2, padx=15, pady=4, sticky="ew")

        tk.Label(self.settings_frame, text="Transcription Lang:", bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", padx=15, pady=4)
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(self.settings_frame, textvariable=self.lang_var, width=15, state="readonly")
        self.lang_combo['values'] = ["Auto (Detect)", "English", "Ukrainian"]
        self.lang_combo.set("Auto (Detect)")
        config_lang = config.get("language", "auto")
        if config_lang == "en":
            self.lang_combo.set("English")
        elif config_lang == "uk":
            self.lang_combo.set("Ukrainian")
        self.lang_combo.grid(row=2, column=1, padx=15, pady=4, sticky="w")

        tk.Label(self.settings_frame, text="Whisper Model:", bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9)).grid(row=3, column=0, sticky="w", padx=15, pady=4)
        self.model_var = tk.StringVar(value=config.get("model_size", "small"))
        self.model_combo = ttk.Combobox(self.settings_frame, textvariable=self.model_var, width=15, state="readonly")
        self.model_combo['values'] = ["tiny", "base", "small", "medium"]
        self.model_combo.grid(row=3, column=1, padx=15, pady=4, sticky="w")

        tk.Label(self.settings_frame, text="Output Directory:", bg=CARD_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 9)).grid(row=4, column=0, sticky="w", padx=15, pady=4)
        self.folder_var = tk.StringVar(value=config.get("output_folder"))
        folder_ent = tk.Entry(self.settings_frame, textvariable=self.folder_var, bg="#11111b", fg=TEXT_COLOR, insertbackground=TEXT_COLOR, bd=0, width=28, font=("Segoe UI", 9))
        folder_ent.grid(row=4, column=1, padx=15, pady=4, sticky="ew")
        
        browse_btn = HoverButton(self.settings_frame, text="Browse...", bg=BTN_BG, fg=TEXT_COLOR, relief=tk.FLAT, bd=0, command=self.browse_folder, font=("Segoe UI", 8))
        browse_btn.grid(row=4, column=2, padx=15, pady=4, sticky="e")

        save_btn = HoverButton(self.settings_frame, text="Save Settings", bg=ACCENT_COLOR, fg="#11111b", font=("Segoe UI", 9, "bold"), relief=tk.FLAT, bd=0, command=self.save_settings)
        save_btn.grid(row=5, column=0, columnspan=3, pady=8)

        # Bind settings changes to auto-save
        self.mic_combo.bind("<<ComboboxSelected>>", self.save_settings)
        self.spk_combo.bind("<<ComboboxSelected>>", self.save_settings)
        self.lang_combo.bind("<<ComboboxSelected>>", self.save_settings)
        self.model_combo.bind("<<ComboboxSelected>>", self.save_settings)
        folder_ent.bind("<FocusOut>", self.save_settings)
        folder_ent.bind("<Return>", self.save_settings)

        # 5. Active Tasks Frame (Dashboard Queue)
        self.tasks_frame = tk.Frame(self.root, bg=CARD_COLOR, bd=1, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.tasks_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        tk.Label(self.tasks_frame, text="ACTIVE TASKS", bg=CARD_COLOR, fg=ACCENT_COLOR, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        
        # Scrollable frame context for tasks
        self.jobs_container = tk.Frame(self.tasks_frame, bg=CARD_COLOR)
        self.jobs_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        
        # Initial empty state
        self.refresh_jobs_gui()

        # 6. Bottom Navigation & Action Buttons Frame
        sec_actions = tk.Frame(self.root, bg=BG_COLOR)
        sec_actions.pack(fill=tk.X, padx=20, pady=5)

        self.folder_btn = HoverButton(
            sec_actions,
            text="Open Folder 📁",
            bg=BTN_BG,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.open_output_folder
        )
        self.folder_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.logs_btn = HoverButton(
            sec_actions,
            text="Open Logs 📄",
            bg=BTN_BG,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.open_log_file
        )
        self.logs_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))

        self.hide_btn = HoverButton(
            sec_actions,
            text="Hide to Tray 📥",
            bg=BTN_BG,
            fg=TEXT_COLOR,
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.hide_window
        )
        self.hide_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        # Fully Exit Button at the very bottom
        exit_frame = tk.Frame(self.root, bg=BG_COLOR)
        exit_frame.pack(fill=tk.X, padx=20, pady=(2, 10))
        
        exit_app_btn = HoverButton(
            exit_frame,
            text="Exit Application ❌",
            bg="#313244",
            fg="#f38ba8",
            active_bg="#f38ba8",
            active_fg="#11111b",
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=5,
            cursor="hand2",
            command=self.exit_app
        )
        exit_app_btn.pack(side=tk.RIGHT)

    def refresh_jobs_gui(self):
        # Clear container
        for widget in self.jobs_container.winfo_children():
            widget.destroy()
            
        if not self.active_jobs:
            lbl = tk.Label(self.jobs_container, text="No active transcription tasks.", bg=CARD_COLOR, fg=DIM_COLOR, font=("Segoe UI", 9, "italic"))
            lbl.pack(pady=15)
            return

        # Render each job row
        for job_id, job in list(self.active_jobs.items()):
            row = tk.Frame(self.jobs_container, bg=CARD_COLOR, pady=4)
            row.pack(fill=tk.X, anchor="w")
            
            # Status and Name
            status = job["status"]
            if status == "Transcribing":
                status_text = f"🔄 [{job['percentage']}%] {job['filename']}"
                color = WARN_COLOR
            elif status == "Completed":
                status_text = f"✅ Completed: {job['filename']}"
                color = SUCCESS_COLOR
            else:
                status_text = f"❌ Failed: {job['filename']}"
                color = REC_COLOR

            header_row = tk.Frame(row, bg=CARD_COLOR)
            header_row.pack(fill=tk.X)
            
            title_lbl = tk.Label(header_row, text=status_text, bg=CARD_COLOR, fg=color, font=("Segoe UI", 9, "bold"), anchor="w")
            title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Dismiss button for finished tasks
            if status in ["Completed", "Failed"]:
                dismiss_btn = tk.Button(
                    header_row, 
                    text="✕", 
                    bg=CARD_COLOR, 
                    fg=DIM_COLOR, 
                    activebackground=CARD_COLOR,
                    activeforeground=TEXT_COLOR,
                    bd=0, 
                    relief=tk.FLAT,
                    font=("Segoe UI", 8, "bold"),
                    cursor="hand2",
                    command=lambda j=job_id: self.remove_job(j)
                )
                dismiss_btn.pack(side=tk.RIGHT)
            
            # Detail labels
            if status == "Transcribing":
                info_text = f"Elapsed: {job['elapsed_str']} | Remaining: ~{job['remaining_str']}"
            elif status == "Completed":
                info_text = f"Finished in {job['elapsed_str']}"
            else:
                info_text = job.get("error_msg", "Error occurred during execution")
                
            info_lbl = tk.Label(row, text=info_text, bg=CARD_COLOR, fg=DIM_COLOR, font=("Segoe UI", 8), anchor="w")
            info_lbl.pack(fill=tk.X, padx=12)
            
            # Determinate Progressbar for active tasks
            if status == "Transcribing":
                pb = ttk.Progressbar(row, orient="horizontal", style="Horizontal.TProgressbar", mode="determinate", maximum=100)
                pb.pack(fill=tk.X, padx=12, pady=(4, 0))
                pb['value'] = job['percentage']

    def load_device_lists(self):
        devices = []
        try:
            with pyaudio.PyAudio() as p:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                for i in range(p.get_device_count()):
                    dev_info = p.get_device_info_by_index(i)
                    if dev_info["hostApi"] == wasapi_info["index"]:
                        is_loopback = dev_info.get("isLoopbackDevice", False)
                        max_input = dev_info.get("maxInputChannels", 0)
                        if is_loopback or max_input > 0:
                            devices.append((i, dev_info["name"], is_loopback))
        except Exception as e:
            logger.error(f"Error enumerating audio devices: {e}")
            
        self.mic_devices = [(idx, name) for idx, name, is_loopback in devices if not is_loopback]
        self.spk_devices = [(idx, name) for idx, name, is_loopback in devices if is_loopback]

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
            self.save_settings()

    def save_settings(self, event=None):
        mic_sel = self.mic_combo.get()
        spk_sel = self.spk_combo.get()
        model_sel = self.model_combo.get()
        folder_sel = self.folder_var.get()
        lang_sel = self.lang_combo.get()

        mic_idx = int(mic_sel.split(":")[0]) if ":" in mic_sel else None
        spk_idx = int(spk_sel.split(":")[0]) if ":" in spk_sel else None
        
        if lang_sel == "English":
            language = "en"
        elif lang_sel == "Ukrainian":
            language = "uk"
        else:
            language = "auto"

        save_config({
            "mic_device_index": mic_idx,
            "speaker_device_index": spk_idx,
            "model_size": model_sel,
            "output_folder": folder_sel,
            "language": language
        })

        self.recorder.mic_idx = mic_idx
        self.recorder.spk_idx = spk_idx

        logger.info("Settings saved successfully.")
        self.trigger_app_state_update("Settings updated")

    def hide_window(self):
        self.root.withdraw()
        logger.info("Window minimized to system tray.")

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        logger.info("Control Panel window restored.")

    def open_output_folder(self):
        config = load_config()
        folder = config.get("output_folder") or os.getcwd()
        if os.path.exists(folder):
            os.startfile(folder)
            logger.info(f"Opened transcripts folder: {folder}")
        else:
            logger.error(f"Folder {folder} does not exist.")

    def open_log_file(self):
        log_file = get_log_filepath()
        if os.path.exists(log_file):
            os.startfile(log_file)
            logger.info(f"Opened log file: {log_file}")
        else:
            logger.error("Log file not found.")

    def trigger_app_state_update(self, detail=""):
        self.root.after(0, lambda: self.update_app_state(detail))

    def update_app_state(self, detail=""):
        if self.is_recording:
            self._update_status_gui("recording", detail)
            self.update_icon("recording")
        else:
            any_processing = any(job["status"] == "Transcribing" for job in self.active_jobs.values())
            if any_processing:
                self._update_status_gui("processing", detail)
                self.update_icon("processing")
            else:
                self._update_status_gui("idle", detail)
                self.update_icon("idle")

    def _update_status_gui(self, state, detail=""):
        if state == "idle":
            self.status_title.config(text="IDLE", fg=DIM_COLOR)
            self.status_desc.config(text=detail or "Ready", fg=DIM_COLOR)
            self.timer_label.config(text="00:00:00")
            self.record_btn.config(text="Start Recording ⏺️", bg=SUCCESS_COLOR, state=tk.NORMAL)
        elif state == "recording":
            self.status_title.config(text="RECORDING...", fg=REC_COLOR)
            self.status_desc.config(text="Capturing microphone & system audio...", fg=TEXT_COLOR)
            self.record_btn.config(text="Stop Recording ⏹️", bg=REC_COLOR, state=tk.NORMAL)
        elif state == "processing":
            self.status_title.config(text="PROCESSING...", fg=WARN_COLOR)
            self.status_desc.config(text="Transcribing audio in the background...", fg=TEXT_COLOR)
            self.record_btn.config(text="Start Recording ⏺️", bg=SUCCESS_COLOR, state=tk.NORMAL)

    def update_timer(self):
        if self.is_recording:
            elapsed = int(time.time() - self.record_start_time)
            hours, remainder = divmod(elapsed, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.timer_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.update_timer)

    def progress_callback(self, job_id, current_sec, total_sec):
        # Redirect progress update to GUI thread safely
        self.root.after(0, lambda: self._update_job_progress(job_id, current_sec, total_sec))

    def _update_job_progress(self, job_id, current_sec, total_sec):
        job = self.active_jobs.get(job_id)
        if not job: return
        
        progress = current_sec / total_sec
        elapsed = time.time() - job["start_time"]
        
        # Estimate remaining time after 3% progress for stability
        if progress > 0.03:
            total_est_time = elapsed / progress
            remaining = total_est_time - elapsed
            rem_min, rem_sec = divmod(int(remaining), 60)
            remaining_str = f"{rem_min:02d}:{rem_sec:02d}"
        else:
            remaining_str = "Calculating..."
            
        elap_min, elap_sec = divmod(int(elapsed), 60)
        elapsed_str = f"{elap_min:02d}:{elap_sec:02d}"
        
        job["progress"] = progress
        job["elapsed_str"] = elapsed_str
        job["remaining_str"] = remaining_str
        job["percentage"] = min(int(progress * 100), 100)
        
        self.refresh_jobs_gui()

    def remove_job(self, job_id):
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
            self.refresh_jobs_gui()

    def process_recording(self, audio_file, job_id):
        try:
            config = load_config()
            out_folder = config.get("output_folder") or os.getcwd()
            os.makedirs(out_folder, exist_ok=True)
            
            job = self.active_jobs[job_id]
            output_txt = os.path.join(out_folder, job["filename"])
            
            logger.info(f"Starting audio transcription for job {job_id}...")
            model_size = config.get("model_size", "small")
            language = config.get("language", "auto")
            
            # Progress callback wrapper
            def progress_cb(current, total):
                self.progress_callback(job_id, current, total)

            transcript_file = transcribe_audio(
                audio_file, 
                model_size=model_size, 
                language=language, 
                output_txt=output_txt,
                progress_callback=progress_cb
            )
            
            if transcript_file:
                logger.info(f"Transcription finished successfully. File: {transcript_file}")
                
                # Update job state
                job["status"] = "Completed"
                # Schedule auto-dismissal after 15 seconds
                self.root.after(15000, lambda: self.remove_job(job_id))
                self.show_notification(f"Saved: {job['filename']}", "Transcription Completed")
            else:
                logger.error("Transcription failed (file not created).")
                job["status"] = "Failed"
                job["error_msg"] = "Speech decoding failed"
                self.show_notification("Whisper failed to decode speech.", "Transcription Failed")
        except Exception as e:
            logger.exception(f"Error during audio processing: {e}")
            if job_id in self.active_jobs:
                job = self.active_jobs[job_id]
                job["status"] = "Failed"
                job["error_msg"] = f"Error: {e}"
            self.show_notification(f"Error: {e}", "Processing Error")
            
        # Clean up temporary WAV file in AppData to prevent disk clutter
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                logger.info(f"Deleted temporary audio recording: {audio_file}")
            except Exception as e:
                logger.error(f"Failed to delete temporary WAV file: {e}")

        # Update app GUI state and refresh jobs
        self.trigger_app_state_update()
        self.root.after(0, self.refresh_jobs_gui)

    def toggle_record(self):
        if not self.is_recording:
            # Start Recording
            self.is_recording = True
            self.record_start_time = time.time()
            self.update_timer()
            self.trigger_app_state_update()
            
            logger.info("Starting audio recording...")
            self.show_notification("Recording started.", "Meeting Assistant")
            try:
                self.recorder.start_recording()
            except Exception as e:
                logger.exception(f"Failed to start recording: {e}")
                self.is_recording = False
                self.trigger_app_state_update(f"Recording failed: {e}")
                self.show_notification(f"Failed to start: {e}", "Recording Failed")
        else:
            # Stop Recording
            self.is_recording = False
            self.trigger_app_state_update()
            
            logger.info("Stopping recording and saving audio...")
            self.show_notification("Recording stopped. Saving audio...", "Meeting Assistant")
            
            now_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            audio_filename = f"meeting_record_{now_str}.wav"
            audio_path = os.path.join(get_app_dir(), audio_filename)
            
            try:
                audio_file = self.recorder.stop_recording(audio_path)
                if audio_file:
                    # Initialize active job tracking
                    job_id = now_str
                    self.active_jobs[job_id] = {
                        "filename": f"meeting_{now_str}.md",
                        "start_time": time.time(),
                        "progress": 0.0,
                        "elapsed_str": "00:00",
                        "remaining_str": "Calculating...",
                        "status": "Transcribing",
                        "percentage": 0
                    }
                    # Update status and icon to processing
                    self.trigger_app_state_update()
                    self.refresh_jobs_gui()
                    
                    # Run Whisper in background thread
                    threading.Thread(target=self.process_recording, args=(audio_file, job_id), daemon=True).start()
                else:
                    logger.error("Audio recording was not saved.")
                    self.trigger_app_state_update("Recording is empty.")
                    self.show_notification("No audio captured.", "Recording Empty")
            except Exception as e:
                logger.exception(f"Error during recording shutdown: {e}")
                self.trigger_app_state_update(f"Failed to save: {e}")
                self.show_notification(f"Failed to save: {e}", "Recording Error")

    def toggle_record_from_tray(self, icon, item):
        self.root.after(0, self.toggle_record)

    def tray_show_window(self, icon, item):
        self.root.after(0, self.show_window)

    def exit_app(self, icon=None, item=None):
        logger.info("Exiting application...")
        if self.is_recording:
            try:
                self.recorder.stop_recording()
            except Exception:
                pass
        try:
            self.recorder.terminate()
        except Exception:
            pass
        if self.icon:
            self.icon.stop()
        self.root.after(0, self.root.destroy)
        sys.exit(0)

    def tray_exit(self, icon, item):
        self.root.after(0, lambda: self.exit_app())

    def run_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem('Control Panel', self.tray_show_window, default=True),
            pystray.MenuItem('Start / Stop Recording', self.toggle_record_from_tray),
            pystray.MenuItem('Exit', self.tray_exit)
        )
        self.icon = pystray.Icon("MeetingAssistant", self.create_image('black'), "Meeting Assistant", menu)
        self.icon.run()

    def start(self):
        # Start pystray in background daemon thread
        threading.Thread(target=self.run_tray, daemon=True).start()
        logger.info("Control Panel started.")
        self.root.mainloop()

if __name__ == "__main__":
    app = MeetingAssistantDashboard()
    app.start()
