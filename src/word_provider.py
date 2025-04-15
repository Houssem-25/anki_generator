"""Provides words for processing, handling input file reading, shuffling, and resume logic."""

import sys
import random
import re
from pathlib import Path
from typing import List, Iterator, Tuple

class WordProvider:
    """Reads, shuffles, filters input words based on existing output."""

    def __init__(self, input_path: Path, output_path: Path):
        self.input_path = input_path
        self.output_path = output_path
        self.words_to_process: List[str] = []
        self.file_mode: str = 'w'
        self._load_and_filter_words()

    def _read_input_words(self) -> List[str]:
        """Reads words from the specified input file."""
        print(f"\n--- Reading Input Words from: {self.input_path} ---")
        try:
            with open(self.input_path, 'r', encoding='utf-8') as infile:
                original_words = [line.strip() for line in infile if line.strip()]
            if not original_words:
                print(f"Error: Input file {self.input_path} is empty.")
                raise ValueError(f"Input file {self.input_path} is empty")
            print(f"Found {len(original_words)} words.")
            return original_words
        except FileNotFoundError:
            print(f"Error: Input file not found at {self.input_path}")
            raise
        except Exception as e:
            print(f"Error reading input file {self.input_path}: {e}")
            sys.exit(1)

    def _determine_words_to_process(self, original_words: List[str]) -> Tuple[List[str], str]:
        """Shuffles words and determines which ones need processing based on existing output."""
        # Shuffle words first
        print("\n--- Shuffling Words ---")
        shuffled_words = original_words[:]
        random.shuffle(shuffled_words)
        print("Words shuffled successfully.")

        # Check for existing output
        processed_words_set = set()
        file_mode = 'w' # Default to write mode

        try:
            if self.output_path.exists() and self.output_path.stat().st_size > 0:
                print(f"\n--- Output file '{self.output_path}' exists. Attempting to resume. ---")
                with open(self.output_path, 'r', encoding='utf-8') as infile:
                    for line in infile:
                        # Extract word from sound tag: [sound:WORD.mp3] or image tag <img src="WORD.png">
                        # Prioritize sound tag as it's more likely to contain the original word form
                        sound_match = re.search(r'\[sound:(.*?)\.mp3\]', line)
                        if sound_match:
                            processed_word = sound_match.group(1)
                            processed_words_set.add(processed_word)
                            continue # Go to next line
                        # Fallback to image tag if no sound tag found
                        img_match = re.search(r'<img src="(.*?)\.png">', line)
                        if img_match:
                             processed_word = img_match.group(1)
                             # Note: image filename might be sanitized word_translation
                             # This might lead to imperfect resume if word != word_translation
                             # Consider storing original word explicitly in output if perfect resume is needed
                             processed_words_set.add(processed_word)

                if processed_words_set:
                    print(f"Found {len(processed_words_set)} potentially processed words in output file.")
                    file_mode = 'a'
                else:
                    print("Output file exists but contains no recognizable processed words. Starting fresh.")
                    file_mode = 'w'
            else:
                 print(f"\n--- Output file '{self.output_path}' not found or empty. Starting fresh generation. ---")
                 file_mode = 'w'

        except Exception as e:
            print(f"Warning: Could not read or parse existing output file '{self.output_path}': {e}")
            print("Proceeding in write mode (will overwrite existing file).")
            file_mode = 'w'
            processed_words_set.clear()

        # Filter the shuffled list
        words_to_process = [word for word in shuffled_words if word not in processed_words_set]

        if file_mode == 'a':
            print(f"\nResuming generation. {len(words_to_process)} words remaining.")
        else:
            print(f"Processing {len(words_to_process)} words.")

        return words_to_process, file_mode

    def _load_and_filter_words(self):
        """Loads words from file and filters based on resume logic."""
        original_words = self._read_input_words()
        self.words_to_process, self.file_mode = self._determine_words_to_process(original_words)

    def get_words(self) -> Iterator[str]:
        """Returns an iterator over the words that need processing."""
        return iter(self.words_to_process)

    def __len__(self) -> int:
        """Returns the number of words remaining to be processed."""
        return len(self.words_to_process)

    def get_file_mode(self) -> str:
        """Determine the file mode for output file based on its existence and content."""
        if not self.output_path.exists() or self.output_path.stat().st_size == 0:
            print(f"\n--- Output file '{self.output_path}' not found or empty. Starting fresh generation. ---")
            return 'w'
        else:
            print(f"\n--- Output file '{self.output_path}' exists. Appending new words. ---")
            return 'a'

