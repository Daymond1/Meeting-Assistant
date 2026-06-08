import os
import sys
import logging
from faster_whisper import WhisperModel

logger = logging.getLogger("MeetingAssistant")

def transcribe_audio(audio_path, model_size="small", language="auto", output_txt="raw_transcript.md", progress_callback=None):
    """
    Transcribes audio file using faster-whisper.
    """
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return None

    logger.info(f"Starting transcription: file={audio_path}, model={model_size}, language={language}")
    
    try:
        logger.info(f"Loading Whisper model '{model_size}' (device: auto, compute_type: int8)...")
        model = WhisperModel(model_size, device="auto", compute_type="int8")
        logger.info("Model loaded successfully.")
        
        transcribe_args = {"beam_size": 5}
        if language and language != "auto":
            transcribe_args["language"] = language
            
        logger.info(f"Decoding audio segments with parameters: {transcribe_args}...")
        segments, info = model.transcribe(audio_path, **transcribe_args)
        
        logger.info(f"Detected language: {info.language} with probability {info.language_probability:.2f}")
        
        total_duration = info.duration
        full_text = []
        for segment in segments:
            seg_text = segment.text.strip()
            if seg_text:
                logger.info(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {seg_text}")
                full_text.append(seg_text)
            if progress_callback and total_duration > 0:
                try:
                    progress_callback(segment.end, total_duration)
                except Exception:
                    pass
                
        final_text = " ".join(full_text)
        
        if not final_text:
            logger.warning("Warning: transcription is empty. No voice/speech detected.")
            final_text = "(Silent recording or speech not recognized)"
        
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(final_text)
            
        logger.info(f"Transcription completed successfully. Transcript saved to: {output_txt}")
        return output_txt
        
    except Exception as e:
        logger.exception(f"Error during audio transcription: {e}")
        return None

if __name__ == "__main__":
    # Test run
    import logging
    logging.basicConfig(level=logging.INFO)
    transcribe_audio("audio.wav")
