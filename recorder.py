import threading
import time
import pyaudiowpatch as pyaudio
import soundfile as sf
import numpy as np
import wave
from config import load_config

class AudioRecorder:
    def __init__(self):
        self.is_recording = False
        self.pa = pyaudio.PyAudio()
        self.mic_stream = None
        self.spk_stream = None
        self.frames = []
        
        self.CHUNK = 2048
        # Standard format for saving
        self.FORMAT = pyaudio.paFloat32
        
        config = load_config()
        self.mic_idx = config.get("mic_device_index")
        self.spk_idx = config.get("speaker_device_index")
        
    def _find_default_devices(self):
        wasapi_info = self.pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_mic = None
        default_spk = None
        
        try:
            default_spk_info = self.pa.get_default_output_device_info()
            # PyAudioWPatch often provides a loopback device for the default output
            for i in range(self.pa.get_device_count()):
                dev = self.pa.get_device_info_by_index(i)
                if dev["hostApi"] == wasapi_info["index"] and dev.get("isLoopbackDevice"):
                    if default_spk_info["name"] in dev["name"]:
                        default_spk = i
                        break
        except Exception:
            pass

        try:
            for i in range(self.pa.get_device_count()):
                dev = self.pa.get_device_info_by_index(i)
                if dev["hostApi"] == wasapi_info["index"] and dev.get("maxInputChannels", 0) > 0 and not dev.get("isLoopbackDevice"):
                    default_mic = i
                    break
        except Exception:
            pass
            
        return default_mic, default_spk

    def start_recording(self):
        if self.is_recording:
            return
            
        self.is_recording = True
        self.frames = []
        self.mic_data = np.zeros(0, dtype=np.float32)
        self.spk_data = np.zeros(0, dtype=np.float32)
        
        mic_id = self.mic_idx
        spk_id = self.spk_idx
        
        def_mic, def_spk = self._find_default_devices()
        
        if mic_id is None:
            mic_id = def_mic
        if spk_id is None:
            spk_id = def_spk

        print(f"Starting recording with Mic ID: {mic_id}, Spk ID: {spk_id}")

        # We will use device-specific sample rates below

        # Callback for microphone
        def mic_callback(in_data, frame_count, time_info, status):
            if self.is_recording:
                # Convert to numpy array and COPY it, because in_data buffer is reused by PyAudio
                audio_data = np.frombuffer(in_data, dtype=np.float32).copy()
                # Store it
                self.mic_frames.append(audio_data)
            return (in_data, pyaudio.paContinue)
            
        # Callback for speaker
        def spk_callback(in_data, frame_count, time_info, status):
            if self.is_recording:
                audio_data = np.frombuffer(in_data, dtype=np.float32).copy()
                self.spk_frames.append(audio_data)
            return (in_data, pyaudio.paContinue)

        self.mic_frames = []
        self.spk_frames = []
        
        # We need to run these in a blocking way using a loop, or use callbacks.
        # Callbacks are easier.
        try:
            if mic_id is not None:
                dev_info = self.pa.get_device_info_by_index(mic_id)
                self.mic_sample_rate = int(dev_info["defaultSampleRate"])
                self.mic_channels = dev_info.get("maxInputChannels", 1)
                
                self.mic_stream = self.pa.open(
                    format=self.FORMAT,
                    channels=self.mic_channels,
                    rate=self.mic_sample_rate,
                    input=True,
                    input_device_index=mic_id,
                    stream_callback=mic_callback,
                    frames_per_buffer=self.CHUNK
                )
        except Exception as e:
            print(f"Failed to open microphone: {e}")

        try:
            if spk_id is not None:
                # WASAPI loopback might require exact channel count/rate of the device
                dev_info = self.pa.get_device_info_by_index(spk_id)
                rate = int(dev_info["defaultSampleRate"])
                channels = dev_info["maxInputChannels"]
                self.spk_sample_rate = rate
                self.spk_channels = channels
                
                self.spk_stream = self.pa.open(
                    format=self.FORMAT,
                    channels=channels,
                    rate=rate,
                    input=True,
                    input_device_index=spk_id,
                    stream_callback=spk_callback,
                    frames_per_buffer=self.CHUNK
                )
        except Exception as e:
            print(f"Failed to open loopback (system audio): {e}")

    def stop_recording(self, output_file="meeting_record.wav"):
        self.is_recording = False
        
        if self.mic_stream:
            self.mic_stream.stop_stream()
            self.mic_stream.close()
            
        if self.spk_stream:
            self.spk_stream.stop_stream()
            self.spk_stream.close()
            
        # Mix the frames
        # This is a basic mix: simply saving what we captured. 
        # Since rates might differ, we'll resample or just mix naively if they match,
        # but soundfile allows saving mono/stereo easily.
        # A robust way is to save Mic to Left channel, Spk to Right channel.
        # For simplicity, if we have both, we'll try to convert to mono and combine, 
        # or just fallback to mic only if spk fails.
        
        # Convert mic list to array
        if self.mic_frames:
            mic_audio = np.concatenate(self.mic_frames)
            mic_ch = getattr(self, "mic_channels", 1)
            if mic_ch > 1:
                mic_audio = mic_audio.reshape(-1, mic_ch).mean(axis=1)
        else:
            mic_audio = np.zeros(0, dtype=np.float32)
            
        if self.spk_frames:
            spk_audio = np.concatenate(self.spk_frames)
            spk_ch = getattr(self, "spk_channels", 1)
            if spk_ch > 1:
                spk_audio = spk_audio.reshape(-1, spk_ch).mean(axis=1)
        else:
            spk_audio = np.zeros(0, dtype=np.float32)
            
        # Resample to a common target rate (e.g. 48000 Hz) to avoid slow-mo/fast-forward
        target_sr = 48000
        
        def resample_np(data, orig_rate, target_rate):
            if orig_rate == target_rate or len(data) == 0:
                return data
            duration = len(data) / orig_rate
            target_len = int(duration * target_rate)
            x_old = np.linspace(0, duration, len(data))
            x_new = np.linspace(0, duration, target_len)
            return np.interp(x_new, x_old, data).astype(np.float32)
            
        mic_rate = getattr(self, "mic_sample_rate", target_sr)
        spk_rate = getattr(self, "spk_sample_rate", target_sr)
        
        mic_resampled = resample_np(mic_audio, mic_rate, target_sr)
        spk_resampled = resample_np(spk_audio, spk_rate, target_sr)
            
        # Pad to same length
        max_len = max(len(mic_resampled), len(spk_resampled))
        mic_padded = np.pad(mic_resampled, (0, max_len - len(mic_resampled)))
        spk_padded = np.pad(spk_resampled, (0, max_len - len(spk_resampled)))
        
        # Mix (average)
        mixed = (mic_padded + spk_padded) / 2.0
        
        if len(mixed) > 0:
            sf.write(output_file, mixed, target_sr)
            print(f"Saved recording to {output_file}")
            return output_file
            
        return None

    def terminate(self):
        self.pa.terminate()

_recorder_instance = None
def record_audio(output_file="audio.wav"):
    # This function is left for backward compatibility, but in tray app we use class
    pass
