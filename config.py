import json
import os
import sys
import logging

def get_app_dir():
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = os.path.expanduser('~')
    app_dir = os.path.join(app_data, "MeetingAssistant")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

def get_config_path():
    return os.path.join(get_app_dir(), "config.json")

def get_log_filepath():
    return os.path.join(get_app_dir(), "meeting_assistant.log")

def load_config():
    config_file = get_config_path()
    default_config = {
        "mic_device_index": None,
        "speaker_device_index": None,
        "output_folder": os.path.join(os.path.expanduser('~'), "Documents", "MeetingTranscripts"),
        "model_size": "small",
        "language": "auto"
    }
    # Ensure default output folder exists
    try:
        os.makedirs(default_config["output_folder"], exist_ok=True)
    except Exception:
        default_config["output_folder"] = os.path.expanduser('~')

    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for k, v in default_config.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    else:
        save_config(default_config)
    return default_config

def save_config(config_data):
    config_file = get_config_path()
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        logger = logging.getLogger("MeetingAssistant")
        logger.error(f"Failed to save config: {e}")

def setup_logging():
    app_dir = get_app_dir()
    log_file = get_log_filepath()
    
    logger = logging.getLogger("MeetingAssistant")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
        
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
    
    # File handler
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to create file handler for logger: {e}", file=sys.stderr)
        
    # Console handler
    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Failed to create console handler: {e}", file=sys.stderr)
        
    return logger

# Automatically set up logging on import
logger = setup_logging()
logger.info("Logging initialized.")
