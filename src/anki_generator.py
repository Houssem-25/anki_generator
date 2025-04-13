import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import re # Import regex module
from . import config
# from .groq_generator import process_words_file # No longer needed here
from . import audio

# Removed AnkiGenerator Class - Unused and redundant

# Removed generate_anki_cards function - Redundant logic, main.py calls process_words_file directly

def write_anki_deck(formatted_lines: List[str], output_file_path: Path, generate_audio_flag: bool = True, original_words: List[str] = None):
    """
    Writes the final Anki deck (.txt format) from pre-processed, formatted lines.

    Processes each line to extract the core German term, generates audio (if enabled),
    prepends the audio tag, and writes the final lines to the output file.

    Args:
        formatted_lines: List of strings, each pre-formatted as "English Part;German Part"
                         by the Groq generator.
        output_file_path: Path to the output .txt file for Anki import.
        generate_audio_flag: Whether to generate audio for the cards.
        original_words: The list of original German words corresponding to formatted_lines, used for audio generation.
    """
    # Ensure output_file_path is a Path object and directory exists
    output_file_path = Path(output_file_path)
    output_dir = output_file_path.parent
    os.makedirs(output_dir, exist_ok=True)

    processed_lines_for_txt = []

    if original_words is None:
        print("Warning: Original words list not provided to write_anki_deck. Audio generation might be inaccurate.")
        # Fallback: try to generate from formatted lines (less reliable)
        original_words = [None] * len(formatted_lines)

    if len(formatted_lines) != len(original_words):
        print(f"Error: Mismatch between formatted lines ({len(formatted_lines)}) and original words ({len(original_words)}). Cannot proceed.")
        return # Or raise an error

    for i, line in enumerate(formatted_lines):
        # Expected format: "English Part;German Part"
        parts = line.split(';', 1)  # Split into max 2 parts
        if len(parts) < 2:
            print(f"Warning: Skipping line due to unexpected format: {line}")
            continue

        english_part = parts[0]
        german_part = parts[1]

        # Get the original word for audio generation
        word_for_audio = original_words[i]

        # Generate audio if flag is enabled using the original word
        sound_tag = ""
        if generate_audio_flag and word_for_audio:
            # Use the original word directly for audio
            sound_tag = audio.generate_audio(word_for_audio)
        elif generate_audio_flag and not word_for_audio:
             print(f"Warning: Missing original word for line index {i}. Cannot generate audio.")

        # Create the final line for the .txt file
        final_line = f"{english_part};{sound_tag}{german_part}"
        processed_lines_for_txt.append(final_line)

    # Write the processed lines to the .txt file
    if processed_lines_for_txt:
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                for line in processed_lines_for_txt:
                    f.write(line + '\n')
            print(f"Generated Anki deck saved to {output_file_path}")
        except Exception as e:
            print(f"Error saving Anki deck to {output_file_path}: {e}")
    else:
        print("Error: No valid lines were processed to generate the Anki deck.")

# Removed if __name__ == "__main__" block - This module is not meant to be run directly 