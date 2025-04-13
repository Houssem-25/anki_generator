import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from . import config
# from .groq_generator import process_words_file # No longer needed here
from . import audio

# Removed AnkiGenerator Class - Unused and redundant

# Removed generate_anki_cards function - Redundant logic, main.py calls process_words_file directly

def write_anki_deck(formatted_lines: List[str], output_file_path: Path, generate_audio_flag: bool = True):
    """
    Writes the final Anki deck (.txt format) from pre-processed, formatted lines.

    Processes each line to extract the core German term, generates audio (if enabled),
    prepends the audio tag, and writes the final lines to the output file.

    Args:
        formatted_lines: List of strings, each pre-formatted as "English Part;German Part"
                         by the Groq generator.
        output_file_path: Path to the output .txt file for Anki import.
        generate_audio_flag: Whether to generate audio for the cards.
    """
    # Ensure output_file_path is a Path object and directory exists
    output_file_path = Path(output_file_path)
    output_dir = output_file_path.parent
    os.makedirs(output_dir, exist_ok=True)

    processed_lines_for_txt = []

    for line in formatted_lines:
        # Expected format: "English Part;German Part"
        parts = line.split(';', 1)  # Split into max 2 parts
        if len(parts) < 2:
            print(f"Warning: Skipping line due to unexpected format: {line}")
            continue

        english_part = parts[0]
        german_part = parts[1]

        # Get the core German word/phrase for audio generation
        # Assume the main term is before the first <br> tag
        german_term_for_audio = german_part.split('<br>')[0]

        # Clean up potential HTML tags (articles) and plural/conjugation info for audio
        clean_term = german_term_for_audio
        for tag in ['<span style="color: rgb(10, 2, 255)">Der</span> ',
                  '<span style="color: rgb(170, 0, 0)">Die</span> ',
                  '<span style="color: rgb(0, 255, 51)">Das</span> ']:
            clean_term = clean_term.replace(tag, '').strip()

        # Remove plural or conjugation info in parentheses if present
        if ' (' in clean_term:
            clean_term = clean_term.split(' (')[0].strip()

        # Generate audio if flag is enabled
        sound_tag = ""
        if generate_audio_flag and clean_term:
            sound_tag = audio.generate_audio(clean_term)
        elif not clean_term:
             print(f"Warning: Could not extract clean term for audio from: {german_term_for_audio}")

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