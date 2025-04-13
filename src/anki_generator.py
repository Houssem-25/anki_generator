import pandas as pd
import os
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from . import config
from .groq_generator import process_words_file
from . import audio

class AnkiGenerator:
    """
    Class for generating Anki cards in a format that can be imported to Anki.
    """
    
    def __init__(self, 
                 input_words_file: Union[str, Path] = config.INPUT_WORDS_FILE,
                 output_csv_file: Union[str, Path] = config.OUTPUT_CSV_FILE):
        """
        Initialize the Anki Generator.
        
        Args:
            input_words_file: Path to the input file containing German words
            output_csv_file: Path to the output CSV file
        """
        self.input_words_file = Path(input_words_file)
        self.output_csv_file = Path(output_csv_file)
    
    def generate_anki_cards(self, generate_audio_flag: bool = True) -> None:
        """
        Generate Anki cards from the input words file and save to CSV.
        
        Args:
            generate_audio_flag: Whether to generate audio for the cards
        """
        print("Processing words...")
        formatted_lines, processed_data = process_words_file(self.input_words_file)
        
        if not formatted_lines:
            print("Error: No data was processed. Check the input file or API access.")
            return
        
        # Parse the formatted lines into data for Anki
        anki_data = []
        for line in formatted_lines:
            # Using the new format with ENGLISH; GERMAN
            parts = line.split(';', 1)  # Split into max 2 parts
            
            if len(parts) < 2:
                print(f"Warning: Line has fewer than expected elements: {line}")
                continue
            
            english_part = parts[0]
            german_part = parts[1]
            
            # Get the German word for audio generation
            # For the audio, we want just the word itself, not examples or additional info
            german_word = german_part.split('<br>')[0]
            
            # Clean up HTML tags and parentheses for audio generation
            clean_word = german_word
            for tag in ['<span style="color: rgb(10, 2, 255)">Der</span> ', 
                      '<span style="color: rgb(170, 0, 0)">Die</span> ', 
                      '<span style="color: rgb(0, 255, 51)">Das</span> ']:
                clean_word = clean_word.replace(tag, '')
            
            # Remove plural or conjugation info in parentheses if present
            if ' (' in clean_word:
                clean_word = clean_word.split(' (')[0]
            
            # Generate audio if flag is enabled
            sound_tag = ""
            if generate_audio_flag:
                sound_tag = audio.generate_audio(clean_word)
            
            # Create dictionary with the main parts
            word_data = {
                'English': english_part,  # English part with translation
                'German': (sound_tag + german_part) if sound_tag else german_part  # Add sound tag to German part
            }
            
            anki_data.append(word_data)
        
        # Create dataframe and save to CSV
        if anki_data:
            # Ensure the output directory exists
            os.makedirs(self.output_csv_file.parent, exist_ok=True)
            
            df = pd.DataFrame(anki_data)
            df.to_csv(self.output_csv_file, index=False, encoding='utf-8')
            print(f"Generated Anki cards saved to {self.output_csv_file}")
        else:
            print("Error: No cards were generated.")

# Function-based API for backward compatibility with main.py
def generate_anki_cards(input_file_path=config.INPUT_WORDS_FILE, 
                       output_file_path=config.ANKI_OUTPUT_FILE,
                       generate_audio_flag=True) -> None:
    """
    Module-level function to generate Anki cards from an input file.
    This provides backward compatibility with the main.py script.
    
    Args:
        input_file_path: Path to the input file containing words to process
        output_file_path: Path to the output file for Anki cards
        generate_audio_flag: Whether to generate audio for the cards
    """
    # Ensure paths are Path objects
    input_file_path = Path(input_file_path)
    output_file_path = Path(output_file_path)
    
    # Process the input file to get formatted lines
    formatted_lines, _ = process_words_file(input_file_path)
    if not formatted_lines:
        print("Error: No data was processed. Check the input file or API access.")
        return
    
    # Use write_anki_cards to handle both CSV and TXT output with sound tags
    write_anki_cards(
        formatted_lines=formatted_lines,
        output_file_path=output_file_path,
        generate_audio_flag=generate_audio_flag
    )

def write_anki_cards(formatted_lines, output_file_path, generate_audio_flag=True):
    """
    Write Anki cards directly from pre-processed formatted lines.
    This avoids double-processing of the input data.
    
    Args:
        formatted_lines: Pre-processed lines in the correct format
        output_file_path: Path to the output file
        generate_audio_flag: Whether to generate audio for the cards
    """
    # Ensure output_file_path is a Path object
    output_file_path = Path(output_file_path)
    
    # Create CSV output path from the text output path
    output_dir = output_file_path.parent
    output_name = output_file_path.stem
    output_csv = output_dir / f"{output_name}.csv"
    
    # Ensure directories exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Process the formatted lines and add audio if needed
    processed_lines = []
    anki_data = []
    
    for line in formatted_lines:
        # Using the new format with ENGLISH; GERMAN
        parts = line.split(';', 1)  # Split into 2 parts
        
        if len(parts) < 2:
            print(f"Warning: Line has fewer than expected elements: {line}")
            continue
            
        english_part = parts[0]
        german_part = parts[1]
        
        # Get the German word for audio generation
        # For the audio, we want just the word itself, not examples or additional info
        german_word = german_part.split('<br>')[0]
        
        # Clean up HTML tags and parentheses for audio generation
        clean_word = german_word
        for tag in ['<span style="color: rgb(10, 2, 255)">Der</span> ', 
                  '<span style="color: rgb(170, 0, 0)">Die</span> ', 
                  '<span style="color: rgb(0, 255, 51)">Das</span> ']:
            clean_word = clean_word.replace(tag, '')
        
        # Remove plural or conjugation info in parentheses if present
        if ' (' in clean_word:
            clean_word = clean_word.split(' (')[0]
        
        # Generate audio if flag is enabled
        sound_tag = ""
        if generate_audio_flag:
            sound_tag = audio.generate_audio(clean_word)
        
        # Create a processed line with sound tags for both TXT and CSV output
        processed_line = f"{english_part};{sound_tag}{german_part}"
        processed_lines.append(processed_line)
        
        # Create dictionary with the main parts for CSV
        word_data = {
            'English': english_part,  # English part with translation
            'German': (sound_tag + german_part) if sound_tag else german_part  # Add sound tag to German part
        }
        
        anki_data.append(word_data)
    
    # Create dataframe and save to CSV
    if anki_data:
        df = pd.DataFrame(anki_data)
        df.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"Generated Anki cards saved to {output_csv}")
    else:
        print("Error: No cards were generated.")
    
    # Also save in the txt format 
    if str(output_file_path).endswith('.txt'):
        try:
            # Write the processed lines with sound tags to the text file
            with open(output_file_path, 'w', encoding='utf-8') as f:
                for line in processed_lines:
                    f.write(line + '\n')
                    
            print(f"Also saved Anki cards in text format to {output_file_path}")
        except Exception as e:
            print(f"Error saving text format: {e}")

def main():
    """
    Main function to generate Anki cards.
    """
    anki_generator = AnkiGenerator()
    anki_generator.generate_anki_cards()

if __name__ == "__main__":
    main() 