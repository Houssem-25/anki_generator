import os
import shutil
from gtts import gTTS
from . import config

def copy_to_anki_media(file_path):
    """Copies the generated audio file to the Anki media directory if configured."""
    if not config.ANKI_MEDIA_DIR or not config.ANKI_MEDIA_DIR.exists():
        print(f"Warning: Anki media directory not found or not configured ({config.ANKI_MEDIA_DIR}). Skipping copy.")
        return False

    try:
        # Ensure the destination directory exists (redundant if check above is thorough, but safe)
        # os.makedirs(config.ANKI_MEDIA_DIR, exist_ok=True)
        shutil.copy2(file_path, config.ANKI_MEDIA_DIR)
        # print(f"File '{os.path.basename(file_path)}' copied successfully to Anki media directory.") # Less verbose
        return True
    except FileNotFoundError:
        print(f"Error: Audio file not found at {file_path}.")
    except PermissionError:
        print(f"Error: Permission denied copying to {config.ANKI_MEDIA_DIR}.")
    except Exception as e:
        print(f"An error occurred during copy to Anki media: {e}")
    return False

def generate_audio(text):
    """Generates a German audio file for the given text using gTTS."""
    # Ensure the audio output directory exists
    config.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_filename = text.replace(" ", "_").replace("/", "_").replace("\\", "_") + ".mp3"
    output_file = config.AUDIO_OUTPUT_DIR / safe_filename
    anki_sound_tag = f"[sound:{safe_filename}]"

    # Avoid regeneration if file exists
    if output_file.exists():
        # print(f"Audio file already exists: {output_file}. Skipping generation.") # Optional: less verbose
        # Optionally, still attempt copy to Anki media if needed
        copy_to_anki_media(output_file)
        return anki_sound_tag

    try:
        tts = gTTS(text=text, lang=config.AUDIO_LANG)
        tts.save(output_file)
        print(f"Generated audio: {output_file}")
        copy_to_anki_media(output_file)
        return anki_sound_tag
    except Exception as e:
        print(f"Error generating audio for '{text}': {e}")
        return "" # Return empty string on failure 