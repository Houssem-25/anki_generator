import argparse
import sys
import os
from pathlib import Path

# Add the project root to the Python path to allow absolute imports from src
# This makes the script runnable as 'python src/main.py' from the root directory
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root.parent))

from src import config
from src import nlp_utils
from src import anki_generator
from src import groq_generator
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
    parser.add_argument(
        "--groq-output",
        type=Path,
        default=None,
        help="Path to save the Groq API processed output (optional)"
    )
    parser.add_argument(
        "--keep-groq-temp",
        action="store_true",
        help="Keep the temporary file created by Groq API processing"
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

    # 1. Check for Groq API Key (mandatory)
    if "GROQ_API_KEY" not in os.environ or not os.environ["GROQ_API_KEY"]:
        print("\nError: Groq API key not found or empty in environment variable GROQ_API_KEY.")
        print("This key is required for processing. Please set it and try again.")
        sys.exit(1) # Exit if key is missing
    else:
        print("\n--- Using Groq API for processing ---")
        # Only warm up the parser if we're using Groq (which is always now)
        nlp_utils.warmup_parser()

    # 2. Process with Groq API
    input_file_for_anki = args.input # Keep track of the original input for cleanup logic
    processed_lines = [] # Initialize to handle potential errors

    try:
        formatted_lines, processed_data = groq_generator.process_words_file(
            input_file_path=args.input,
            output_file_path=args.groq_output # Optional Groq output save path
        )

        # Check if formatted_lines were generated
        if not formatted_lines:
            print("Error: No data was processed by Groq. Check the input file or API access.")
            sys.exit(1)

        # Store formatted lines for Anki generation
        processed_lines = formatted_lines

        # Create a temporary file if keep-groq-temp is requested or for debugging
        # We don't strictly need the temp file anymore unless --keep-groq-temp is used
        temp_file_path = None
        if args.keep_groq_temp:
            temp_file_path = args.input.parent / f"{args.input.stem}_groq_processed{args.input.suffix}"
            try:
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    for line in formatted_lines:
                        f.write(line + '\n')
                print(f"Saved Groq API processed content to temporary file: {temp_file_path}")
            except Exception as e:
                 print(f"Warning: Could not write temporary Groq file: {e}")
                 temp_file_path = None # Reset if writing failed

    except Exception as e:
        print(f"\nError during Groq API processing: {e}")
        print("Please check your input file, Groq API key, and network connection.")
        sys.exit(1) # Exit on Groq processing error

    # 3. Generate Anki Cards using the processed lines
    print("\n--- Generating Anki Cards ---")
    print(f"Original input file: {args.input}")
    print(f"Output file: {args.output}")
    if config.ANKI_MEDIA_DIR:
        print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
    else:
        print("Anki media sync directory: Not configured or found.")

    try:
        # Use write_anki_cards with the pre-processed formatted_lines
        anki_generator.write_anki_cards(
            formatted_lines=processed_lines,
            output_file_path=args.output,
            generate_audio_flag=(not args.no_audio)
        )
    except Exception as e:
        print(f"\nError during Anki card generation: {e}")
        sys.exit(1)

    # 4. Clean up (Only relevant if keep-groq-temp was used and succeeded)
    # No automatic cleanup needed unless keep-groq-temp was specifically used to create a file.
    if args.keep_groq_temp and temp_file_path:
         print(f"Kept temporary Groq processed file as requested: {temp_file_path}")
    elif not args.keep_groq_temp:
        # Optional: Could add logic here to delete a previously existing temp file if desired,
        # but currently no temp file is created unless --keep-groq-temp is specified.
        pass

    print("\n--- Anki Card Generation Finished ---")


if __name__ == "__main__":
    main()