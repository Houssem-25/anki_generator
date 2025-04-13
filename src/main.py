import argparse
import sys
import os
from pathlib import Path

# Add the project root to the Python path to allow absolute imports from src
# This makes the script runnable as 'python src/main.py' from the root directory
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root.parent))

from src import config
# from src import nlp_utils # Removed - Unused
from src import anki_generator
from src import groq_generator
# Note: audio module is used by anki_generator

def main():
    """Main function to parse arguments and run the Anki card generation process."""
    parser = argparse.ArgumentParser(description="Generate Anki cards from a list of German words.")

    # --- Argument Definitions ---
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=config.INPUT_WORDS_FILE,
        help=f"Path to the input file containing German words (one per line). Default: {config.INPUT_WORDS_FILE}"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=config.ANKI_OUTPUT_FILE,
        help=f"Path to the output Anki file (.txt format). Default: {config.ANKI_OUTPUT_FILE}"
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip audio generation and copying to Anki media folder."
    )
    parser.add_argument(
        "--anki-media-path",
        type=Path,
        default=None,
        help="Path to your Anki profile's collection.media folder. If provided, audio files will be copied here."
    )
    # Removed --groq-output and --keep-groq-temp arguments - Simplified flow

    args = parser.parse_args()

    # --- Configuration Update ---
    # Set the global ANKI_MEDIA_DIR in the config module if the argument is provided
    if args.anki_media_path:
         print(f"Using specified Anki media path: {args.anki_media_path}")
         # Ensure the path exists before setting it in config
         if not args.anki_media_path.is_dir():
             print(f"Warning: Anki media path provided does not exist or is not a directory: {args.anki_media_path}")
             print("Audio files will be generated but not copied.")
             config.ANKI_MEDIA_DIR = None # Keep it None if path is invalid
         else:
             config.ANKI_MEDIA_DIR = args.anki_media_path # Update global config
    else:
        config.ANKI_MEDIA_DIR = None # Explicitly None if not provided

    # --- Execution ---
    print("\n--- Starting Anki Card Generation ---")

    # 1. Check for Groq API Key (mandatory)
    if "GROQ_API_KEY" not in os.environ or not os.environ["GROQ_API_KEY"]:
        print("\nError: Groq API key not found or empty in environment variable GROQ_API_KEY.")
        print("This key is required for processing. Please set it and try again.")
        sys.exit(1) # Exit if key is missing

    print("\n--- Reading Input Words ---")
    original_words = []
    try:
        with open(args.input, 'r', encoding='utf-8') as infile:
            original_words = [line.strip() for line in infile.readlines() if line.strip()]
        if not original_words:
            print(f"Error: Input file {args.input} is empty or contains only whitespace.")
            sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file {args.input}: {e}")
        sys.exit(1)

    print("\n--- Processing words with Groq API ---")
    # Removed nlp_utils.warmup_parser() - Unnecessary

    # 2. Process words file using Groq to get formatted lines
    formatted_lines = [] # Initialize
    try:
        # Call process_words_file without the output_file_path argument
        formatted_lines, _ = groq_generator.process_words_file(
            input_file_path=args.input
        )

        if not formatted_lines:
            print("Error: No data was processed by Groq. Check input file or API connection.")
            sys.exit(1)

    except Exception as e:
        print(f"\nError during Groq API processing: {e}")
        print("Please check your input file, Groq API key, and network connection.")
        sys.exit(1) # Exit on Groq processing error

    # 3. Generate Anki Deck (TXT file and Audio)
    print("\n--- Generating Anki Deck ---")
    print(f"Input file: {args.input}")
    print(f"Output deck file: {args.output}")
    if config.ANKI_MEDIA_DIR:
        print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
    else:
        print("Anki media sync directory: Not specified or path invalid.")

    try:
        # Call the refactored function in anki_generator
        anki_generator.write_anki_deck(
            formatted_lines=formatted_lines,
            output_file_path=args.output,
            generate_audio_flag=(not args.no_audio),
            original_words=original_words # Pass the original words
        )
    except Exception as e:
        print(f"\nError during Anki deck generation: {e}")
        sys.exit(1)

    # Removed cleanup logic related to temp files
    print("\n--- Anki Card Generation Finished ---")


if __name__ == "__main__":
    main()