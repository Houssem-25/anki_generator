import argparse
import sys
from pathlib import Path

# Add the project root to the Python path to allow absolute imports from src
# This makes the script runnable as 'python src/main.py' from the root directory
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root.parent))

from src import config
from src import nlp_utils
from src import anki_generator
# Note: audio module is used by anki_generator, translation too.
# data_loader is used by anki_generator implicitly upon import.

def main():
    """Main function to parse arguments and run the Anki card generation process."""
    parser = argparse.ArgumentParser(description="Generate Anki cards from a list of German words.")

    # --- Argument Definitions ---
    parser.add_argument(
        "-i", "--input",
        type=Path,
        default=config.INPUT_WORDS_FILE,
        help=f"Path to the input file (default: {config.INPUT_WORDS_FILE})"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=config.ANKI_OUTPUT_FILE,
        help=f"Path to the output Anki file (default: {config.ANKI_OUTPUT_FILE})"
    )
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip audio generation and copying to Anki media."
    )
    parser.add_argument(
        "--anki-media-path",
        type=Path,
        default=None, # Default to None, use config value if not provided
        help=f"Override Anki media collection path (default from config: {config.ANKI_MEDIA_DIR or 'Not Found'})"
    )

    args = parser.parse_args()

    # --- Configuration Overrides ---
    # Update config based on command-line arguments ONLY if they are provided
    anki_media_path_override = args.anki_media_path or config.ANKI_MEDIA_DIR
    if args.anki_media_path:
         print(f"Using specified Anki media path: {args.anki_media_path}")
         config.ANKI_MEDIA_DIR = args.anki_media_path # Update global config

    # --- Execution ---
    print("\n--- Starting Anki Card Generation ---")

    # 1. Warm up NLP components
    nlp_utils.warmup_parser()

    # 2. Generate Anki cards
    print(f"Input file: {args.input}")
    print(f"Output file: {args.output}")
    if config.ANKI_MEDIA_DIR:
        print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
    else:
        print("Anki media sync directory: Not configured or found.")

    # Pass the 'generate_audio' flag based on '--no-audio'
    anki_generator.generate_anki_cards(
        input_file_path=args.input,
        output_file_path=args.output,
        generate_audio_flag=(not args.no_audio) # Pass the flag
    )

    print("\n--- Anki Card Generation Finished ---")


if __name__ == "__main__":
    main()