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
        "--use-groq",
        action="store_true",
        help="Use Groq API to generate example sentences and translations"
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

    # 1. Warm up NLP components
    nlp_utils.warmup_parser()

    # 2. Check if Groq API should be used
    if args.use_groq:
        print("\n--- Using Groq API to generate example sentences and translations ---")
        formatted_lines, _ = groq_generator.process_words_file(
            input_file_path=args.input,
            output_file_path=args.groq_output
        )
        
        # Create a temporary file with the formatted output from Groq
        temp_input_file = args.input.parent / f"{args.input.stem}_groq_processed{args.input.suffix}"
        with open(temp_input_file, 'w', encoding='utf-8') as f:
            for line in formatted_lines:
                f.write(line + '\n')
                
        print(f"Created temporary file with Groq API processed content: {temp_input_file}")
        
        # Use the temporary file as input for Anki card generation
        input_file_for_anki = temp_input_file
    else:
        input_file_for_anki = args.input

    # 3. Generate Anki cards
    print(f"Input file: {input_file_for_anki}")
    print(f"Output file: {args.output}")
    if config.ANKI_MEDIA_DIR:
        print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
    else:
        print("Anki media sync directory: Not configured or found.")

    # Pass the 'generate_audio' flag based on '--no-audio'
    anki_generator.generate_anki_cards(
        input_file_path=input_file_for_anki,
        output_file_path=args.output,
        generate_audio_flag=(not args.no_audio) # Pass the flag
    )

    # Clean up temporary file if created
    if args.use_groq and input_file_for_anki != args.input and not args.keep_groq_temp:
        try:
            import os
            os.remove(input_file_for_anki)
            print(f"Cleaned up temporary file: {input_file_for_anki}")
        except Exception as e:
            print(f"Failed to clean up temporary file: {e}")
    elif args.use_groq and args.keep_groq_temp:
        print(f"Kept temporary Groq processed file: {input_file_for_anki}")

    print("\n--- Anki Card Generation Finished ---")


if __name__ == "__main__":
    main()