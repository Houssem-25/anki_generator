import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent  # Project root directory
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "anki_output"  # Changed from 'anki/' to 'anki_output/' for clarity

# Input data files
# GERMAN_TO_ENG_PICKLE = DATA_DIR / "german_to_eng.pickle" # Removed - Unused
# GERMAN_TO_ENG_IDS_PICKLE = DATA_DIR / "german_to_eng_ids.pickle" # Removed - Unused
# NEW_ENGLISH_TEXTS_PICKLE = DATA_DIR / "new_english_texts.pickle" # Removed - Unused
INPUT_WORDS_FILE = DATA_DIR / "new_words.txt"

# Output files
ANKI_OUTPUT_FILE = OUTPUT_DIR / "anki.txt"
OUTPUT_CSV_FILE = OUTPUT_DIR / "anki_cards.csv"  # CSV output for Anki cards
AUDIO_OUTPUT_DIR = OUTPUT_DIR / "audio" # Store generated audio within the output dir
IMAGE_OUTPUT_DIR = OUTPUT_DIR / "images" # Store generated images within the output dir

# Anki media directory (Set via command-line argument only)
ANKI_MEDIA_DIR = None # This will be updated by main.py based on the arg

# --- Constants ---
# HTML Color spans for noun genders
GENDER_TO_ARTICLE_HTML = {
    "m": '<span style="color: rgb(10, 2, 255)">Der</span> ',
    "f": '<span style="color: rgb(170, 0, 0)"> Die</span> ',  # Note: space before "Die"
    "n": '<span style="color: rgb(0, 255, 51)">Das</span> ',
    "p": '<span style="color: rgb(170, 0, 0)"> Die</span> ',  # Note: space before "Die"
    "pl": '<span style="color: rgb(170, 0, 0)"> Die</span> '  # Note: space before "Die"
}

# Language settings (Potentially still used by gTTS, keep for now)
SOURCE_LANG = 'german'
TARGET_LANG = 'english'
AUDIO_LANG = 'de'

# --- Other Settings ---
# MAX_EXAMPLE_SENTENCE_LENGTH = 10 # Removed - Likely unused, Groq controls examples
# WARMUP_ATTEMPTS = 10 # Removed - Unused 