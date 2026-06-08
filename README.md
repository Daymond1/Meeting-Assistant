# Meeting Assistant

Meeting Assistant is a lightweight Windows application that runs quietly in your system tray. It records both your microphone and your system audio (speakers) simultaneously using WASAPI, and automatically transcribes the conversation locally using the highly efficient `faster-whisper` AI model.

The tool is completely local, ensuring your meetings remain private and do not require uploading audio to third-party cloud services.

## ✨ Features

- **Simultaneous Recording**: Captures both your microphone and system audio without needing Virtual Audio Cables.
- **Local AI Transcription**: Uses `faster-whisper` to transcribe audio quickly and accurately directly on your machine.
- **Tray-First Focus**: Launches silently in the system tray. The Control Panel window is displayed only when explicitly requested.
- **Desktop Notifications**: Displays system toast alerts when recording starts/stops and when transcription finishes.
- **Concurrent Processing (Multi-threading)**: Allows you to start recording a new meeting immediately while a previous one is still being transcribed.
- **Task Dashboard & ETA Tracking**: Displays a real-time progress bar, elapsed time, and remaining time (ETA) for each active background transcription.
- **Target Language Enforcement**: Select Ukrainian or English to prevent Whisper's auto-detection from misidentifying silent audio or background noise.
- **Auto-Saving Settings**: Changes to audio devices, language, or output folders are persisted automatically on selection.
- **Portable**: Can be compiled into a standalone directory using PyInstaller.

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Windows (WASAPI is used for loopback recording)
- FFmpeg (Required by `faster-whisper` under the hood)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/meeting-assistant.git
   cd meeting-assistant
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App
Start the app by running:
```bash
python main.py
```
A black circle icon will appear in your system tray. 
- Double-click the tray icon (or right-click and select **Control Panel**) to open the configuration dashboard.
- Select your preferred Microphone, Speakers, Transcription Language, and output directory. Settings are saved automatically!
- Click **Start Recording** (or select **Start / Stop Recording** from the tray menu). The icon turns red, and a notification appears.
- Click **Stop Recording**. The icon turns yellow, and transcription begins in the background. You can track its progress (percentage, elapsed/remaining time) in the Active Tasks list at the bottom of the Control Panel.
- Transcripts are saved as Markdown (`.md`) files in your chosen folder.

## 🛠 Building the Executable (Optional)
If you want to package the app into a standalone folder with all dependencies included (no Python installation required on the target machine), use PyInstaller:
```bash
pip install pyinstaller
pyinstaller "Meeting Assistant.spec" --noconfirm
```
The compiled executable and its resources will be created in the `dist/Meeting Assistant` folder.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
