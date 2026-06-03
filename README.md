# Meeting Assistant

Meeting Assistant is a lightweight Windows application that runs quietly in your system tray. It records both your microphone and your system audio (speakers) simultaneously using WASAPI, and then automatically transcribes the conversation locally using the highly efficient `faster-whisper` AI model.

The tool is completely local, ensuring your meetings remain private and do not require uploading audio to third-party cloud services.

## ✨ Features

- **Simultaneous Recording**: Captures both your microphone and system audio without needing Virtual Audio Cables.
- **Local AI Transcription**: Uses `faster-whisper` to transcribe audio quickly and accurately directly on your machine.
- **System Tray Integration**: Unobtrusive tray icon that lets you start and stop recording with a single click.
- **Auto-resampling**: Prevents audio "slow-mo" or "chipmunk" effects by automatically resampling mixed audio tracks to a standard sample rate.
- **Configurable Settings**: Choose your preferred microphone, speaker (loopback device), and the target directory for your Markdown (`.md`) transcripts.
- **Portable**: Can be compiled into a standalone `.exe` using PyInstaller.

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
- Right-click it and open **Settings** to configure your audio devices and output folder.
- Click the icon to start recording (it will turn red).
- Click again to stop. The audio will be automatically transcribed and saved as a Markdown file in your chosen folder.

## 🛠 Building the Executable (Optional)
If you want to package the app into a standalone `.exe` file without needing Python installed on the target machine, use PyInstaller:
```bash
pip install pyinstaller
python -m pyinstaller --noconsole --onedir --name "Meeting Assistant" --collect-all faster_whisper --collect-all ctranslate2 main.py
```
The executable will be located in the `dist/Meeting Assistant` folder.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
