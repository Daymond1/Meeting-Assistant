import tkinter as tk
from tkinter import ttk, filedialog
import os
import pyaudiowpatch as pyaudio
from config import load_config, save_config

def get_audio_devices():
    """Returns a list of tuple (index, name, is_loopback) for available devices"""
    devices = []
    
    # We must use PyAudioWPatch to get the WASAPI loopback devices
    with pyaudio.PyAudio() as p:
        info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        
        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            # Only consider WASAPI devices
            if dev_info["hostApi"] == info["index"]:
                # Check for loopback (speakers) or input (mic)
                is_loopback = dev_info.get("isLoopbackDevice", False)
                max_input = dev_info.get("maxInputChannels", 0)
                
                if is_loopback or max_input > 0:
                    devices.append((i, dev_info["name"], is_loopback))
    return devices

def open_settings():
    root = tk.Tk()
    root.title("Meeting Assistant Settings")
    root.geometry("400x350")
    
    config = load_config()
    
    devices = get_audio_devices()
    
    # Separate lists
    mic_devices = [(idx, name) for idx, name, is_loopback in devices if not is_loopback]
    speaker_devices = [(idx, name) for idx, name, is_loopback in devices if is_loopback]
    
    tk.Label(root, text="Select Microphone:").pack(pady=(10, 0))
    mic_var = tk.StringVar()
    mic_combo = ttk.Combobox(root, textvariable=mic_var, width=50, state="readonly")
    
    mic_display_list = [f"{idx}: {name}" for idx, name in mic_devices]
    mic_combo['values'] = ["Default"] + mic_display_list
    
    # Pre-select
    if config.get("mic_device_index") is not None:
        idx_str = str(config["mic_device_index"])
        match = next((x for x in mic_display_list if x.startswith(idx_str + ":")), None)
        if match:
            mic_combo.set(match)
        else:
            mic_combo.set("Default")
    else:
        mic_combo.set("Default")
    
    mic_combo.pack(pady=5)
    
    tk.Label(root, text="Select Speaker (System Audio):").pack(pady=(10, 0))
    spk_var = tk.StringVar()
    spk_combo = ttk.Combobox(root, textvariable=spk_var, width=50, state="readonly")
    
    spk_display_list = [f"{idx}: {name}" for idx, name in speaker_devices]
    spk_combo['values'] = ["Default"] + spk_display_list
    
    if config.get("speaker_device_index") is not None:
        idx_str = str(config["speaker_device_index"])
        match = next((x for x in spk_display_list if x.startswith(idx_str + ":")), None)
        if match:
            spk_combo.set(match)
        else:
            spk_combo.set("Default")
    else:
        spk_combo.set("Default")
        
    spk_combo.pack(pady=5)
    
    # Output Folder
    tk.Label(root, text="Output Folder for Transcripts:").pack(pady=(10, 0))
    folder_frame = tk.Frame(root)
    folder_frame.pack(pady=5)
    
    folder_var = tk.StringVar(value=config.get("output_folder") or os.getcwd())
    tk.Entry(folder_frame, textvariable=folder_var, width=40, state="readonly").pack(side=tk.LEFT, padx=(0, 5))
    
    def choose_folder():
        folder = filedialog.askdirectory(initialdir=folder_var.get())
        if folder:
            folder_var.set(folder)
            
    tk.Button(folder_frame, text="Browse", command=choose_folder).pack(side=tk.LEFT)
    
    def save():
        mic_sel = mic_combo.get()
        spk_sel = spk_combo.get()
        
        mic_idx = int(mic_sel.split(":")[0]) if mic_sel != "Default" else None
        spk_idx = int(spk_sel.split(":")[0]) if spk_sel != "Default" else None
        
        save_config({
            "mic_device_index": mic_idx,
            "speaker_device_index": spk_idx,
            "output_folder": folder_var.get()
        })
        root.destroy()
        
    tk.Button(root, text="Save", command=save, width=15).pack(pady=20)
    
    root.mainloop()

if __name__ == "__main__":
    open_settings()
