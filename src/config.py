import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent.parent  # Project root directory
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "anki_output"  # Changed from 'anki/' to 'anki_output/' for clarity

# Input data files
# GERMAN_TO_ENG_PICKLE = DATA_DIR / "german_to_eng.pickle" # Removed - Unused
# GERMAN_TO_ENG_IDS_PICKLE = DATA_DIR / "german_to_eng_ids.pickle" # Removed - Unused
# NEW_ENGLISH_TEXTS_PICKLE = DATA_DIR / "new_english_texts.pickle" # Removed - Unused
INPUT_WORDS_FILE = DATA_DIR / "input_words.txt"

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

# --- API Keys & Credentials ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")

# --- Debug Settings ---
DEBUG = False

def setup_config(args):
    """Updates configuration based on parsed command-line arguments."""
    global ANKI_MEDIA_DIR, DEBUG # We need to modify the global variables

    # Set DEBUG mode based on command-line argument
    if hasattr(args, 'debug') and args.debug:
        DEBUG = True
        print("\n--- Debug mode enabled. Full LLM responses will be printed. ---")

    # Set the global ANKI_MEDIA_DIR in the config module if the argument is provided
    if args.anki_media_path:
        print(f"Using specified Anki media path: {args.anki_media_path}")
        # Ensure the path exists before setting it in config
        if not args.anki_media_path.is_dir():
            print(f"Warning: Anki media path provided does not exist or is not a directory: {args.anki_media_path}")
            print("Audio/Image files will be generated but not copied.")
            ANKI_MEDIA_DIR = None # Keep it None if path is invalid
        else:
            ANKI_MEDIA_DIR = args.anki_media_path # Update global config
    else:
        ANKI_MEDIA_DIR = None # Explicitly None if not provided

    # Ensure output directories exist based on arguments and configuration
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if ANKI_MEDIA_DIR or (CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN and not args.no_image):
        IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if ANKI_MEDIA_DIR or not args.no_audio:
        AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def check_prerequisites(args):
    """Checks for necessary API keys and credentials."""
    # 1. Groq API Key
    if not GROQ_API_KEY:
        print("\nError: Groq API key not found or empty (GROQ_API_KEY). Set it in the .env file.")
        return False

    # 2. Cloudflare Credentials (Optional for Images)
    can_generate_images = False
    if not args.no_image:
        if CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
            print("\n--- Cloudflare credentials found. Image generation enabled. ---")
            can_generate_images = True
        else:
            print("\nWarning: Cloudflare credentials missing. Skipping image generation.")
            print("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in .env to enable images.")
    return True, can_generate_images