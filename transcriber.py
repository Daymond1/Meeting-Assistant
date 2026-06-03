from faster_whisper import WhisperModel
import os

def transcribe_audio(audio_path, model_size="small", output_txt="raw_transcript.md"):
    """
    Транскрибує аудіофайл за допомогою faster-whisper.
    """
    if not os.path.exists(audio_path):
        print(f"Файл {audio_path} не знайдено.")
        return None

    print(f"Завантаження моделі '{model_size}' та початок транскрибації...")
    
    # Завантажуємо модель (fp16 для швидкості, якщо підтримується, інакше int8/fp32)
    # compute_type="int8" є безпечним вибором для процесорів та слабших відеокарт.
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    
    # beam_size=5 є хорошим балансом між швидкістю та якістю
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    print(f"Визначена мова: {info.language} з імовірністю {info.language_probability:.2f}")
    
    full_text = []
    print("Транскрибування:")
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
        full_text.append(segment.text)
        
    final_text = " ".join(full_text)
    
    # Зберігаємо сирий транскрипт у вказаний файл
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(final_text)
        
    print(f"\nТранскрибацію завершено. Текст збережено у {output_txt}")
    return output_txt

if __name__ == "__main__":
    # Тестовий запуск
    transcribe_audio("audio.wav")
