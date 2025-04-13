import os
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent  # Project root directory
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "anki_output"  # Changed from 'anki/' to 'anki_output/' for clarity

# Input data files
GERMAN_TO_ENG_PICKLE = DATA_DIR / "german_to_eng.pickle"
GERMAN_TO_ENG_IDS_PICKLE = DATA_DIR / "german_to_eng_ids.pickle"
NEW_ENGLISH_TEXTS_PICKLE = DATA_DIR / "new_english_texts.pickle"
INPUT_WORDS_FILE = DATA_DIR / "new_words.txt"

# Output files
ANKI_OUTPUT_FILE = OUTPUT_DIR / "anki.txt"
AUDIO_OUTPUT_DIR = OUTPUT_DIR / "audio" # Store generated audio within the output dir

# Anki media directory (Consider making this configurable via environment variable or config file)
ANKI_MEDIA_DIR_ENV = "/media/houssem/0082677582676DDA/Users/Houssem/AppData/Roaming/"
ANKI_MEDIA_DIR = Path(ANKI_MEDIA_DIR_ENV) / 'Anki2' / 'Houssem' / 'collection.media' if ANKI_MEDIA_DIR_ENV else None

# --- Constants ---
# HTML Color spans for noun genders
GENDER_TO_ARTICLE_HTML = {
    "m": '<span style="color: rgb(10, 2, 255)">Der</span> ',
    "f": '<span style="color: rgb(170, 0, 0)">Die</span> ', # Corrected color span tag
    "n": '<span style="color: rgb(0, 255, 51)">Das</span> ',
    "p": '<span style="color: rgb(170, 0, 0)">Die</span> ',
    "pl": '<span style="color: rgb(170, 0, 0)">Die</span> '
}

# Translation settings
SOURCE_LANG = 'german'
TARGET_LANG = 'english'
AUDIO_LANG = 'de'

# --- Other Settings ---
MAX_EXAMPLE_SENTENCE_LENGTH = 10 # Max words in an example sentence
WARMUP_ATTEMPTS = 10 