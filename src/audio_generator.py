import os
import shutil
from gtts import gTTS
from pathlib import Path

from . import config

def copy_to_anki_media(file_path):
    """Copies a file to the Anki media directory if configured."""
    if config.ANKI_MEDIA_DIR:
        if not config.ANKI_MEDIA_DIR.is_dir():
            print(f"Warning: Anki media directory not found or not a directory: {config.ANKI_MEDIA_DIR}. Skipping copy.")
            return False
        try:
            dest_path = config.ANKI_MEDIA_DIR / file_path.name
            shutil.copy2(file_path, dest_path)
            print(f"    Media file copied to: {dest_path}")
            return True
        except Exception as e:
            print(f"    Warning: Failed to copy media '{file_path.name}' to Anki directory: {e}")
            return False
    return False

def generate_audio(text: str, safe_filename_base: str) -> str:
    """
    Generates audio for the given text using gTTS, saves it using the provided
    safe filename base, and copies it to the Anki media directory if configured.

    Args:
        text (str): The text to synthesize.
        safe_filename_base (str): The pre-sanitized base filename (without extension).

    Returns:
        str: The Anki [sound:] tag if successful, otherwise an empty string.
    """
    if not text or not safe_filename_base:
        print("Warning: generate_audio called with empty text or filename base.")
        return ""

    try:
        # Ensure output directories exist (moved from WordProcessor for safety)
        config.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if config.ANKI_MEDIA_DIR:
             config.ANKI_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

        # Construct paths using the provided safe name
        safe_filename_with_ext = safe_filename_base + ".mp3"
        output_file = config.AUDIO_OUTPUT_DIR / safe_filename_with_ext
        anki_sound_tag = f"[sound:{safe_filename_with_ext}]"

        # Check if file already exists locally
        if output_file.exists():
            # print(f"Audio file already exists: {output_file}. Skipping generation.")
            # Ensure it's copied even if generation is skipped
            copy_to_anki_media(output_file)
            return anki_sound_tag

        # Generate audio
        tts = gTTS(text=text, lang='de')
        tts.save(output_file)
        print(f"    Audio saved to: {output_file}")

        # Copy to Anki media directory
        copy_to_anki_media(output_file)

        return anki_sound_tag

    except Exception as e:
        print(f"    Error generating audio for '{text}': {e}")
        return "" # Return empty string on failure