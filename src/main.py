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
        "--no-groq",
        action="store_true",
        help="Skip using Groq API to generate example sentences and translations (disables default LLM behavior)"
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

    # 1. Check if Groq API should be used (default is to use it unless --no-groq is specified)
    use_groq = not args.no_groq
    
    # 2. Check if Groq API key is available when needed
    has_groq_api_key = "GROQ_API_KEY" in os.environ and os.environ["GROQ_API_KEY"]
    
    if use_groq:
        if not has_groq_api_key:
            print("\nWarning: Groq API key not found in environment. Set GROQ_API_KEY to use LLM features.")
            print("Falling back to traditional processing without LLM.")
            use_groq = False
        else:
            # Only warm up the parser if we're using Groq
            nlp_utils.warmup_parser()
            print("\n--- Using Groq API to generate example sentences and translations (default behavior) ---")
    else:
        print("\n--- Skipping Groq API processing (using traditional method) ---")
    
    # 3. Process with Groq API if enabled
    input_file_for_anki = args.input
    if use_groq:
        try:
            formatted_lines, processed_data = groq_generator.process_words_file(
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
            
            # Pass the formatted_lines directly to generate_anki_cards to avoid reprocessing
            # Instead of using the temporary file as input and processing again
            print(f"Input file: {input_file_for_anki}")
            print(f"Output file: {args.output}")
            if config.ANKI_MEDIA_DIR:
                print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
            else:
                print("Anki media sync directory: Not configured or found.")

            # Pass the 'generate_audio' flag based on '--no-audio' and use the pre-processed formatted_lines
            try:
                anki_generator.write_anki_cards(
                    formatted_lines=formatted_lines,
                    output_file_path=args.output,
                    generate_audio_flag=(not args.no_audio)
                )
            except Exception as e:
                print(f"Error during Anki card generation: {e}")
                sys.exit(1)
                
        except Exception as e:
            print(f"Error during Groq API processing: {e}")
            print("Falling back to using the original input file.")
            input_file_for_anki = args.input
            
            # Process normally with the original input file
            print(f"Input file: {input_file_for_anki}")
            print(f"Output file: {args.output}")
            if config.ANKI_MEDIA_DIR:
                print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
            else:
                print("Anki media sync directory: Not configured or found.")

            # Pass the 'generate_audio' flag based on '--no-audio'
            try:
                anki_generator.generate_anki_cards(
                    input_file_path=input_file_for_anki,
                    output_file_path=args.output,
                    generate_audio_flag=(not args.no_audio)
                )
            except Exception as e:
                print(f"Error during Anki card generation: {e}")
                sys.exit(1)
                
    else:
        # Not using Groq, process normally with the original input file
        print(f"Input file: {input_file_for_anki}")
        print(f"Output file: {args.output}")
        if config.ANKI_MEDIA_DIR:
            print(f"Anki media sync directory: {config.ANKI_MEDIA_DIR}")
        else:
            print("Anki media sync directory: Not configured or found.")

        # Pass the 'generate_audio' flag based on '--no-audio'
        try:
            anki_generator.generate_anki_cards(
                input_file_path=input_file_for_anki,
                output_file_path=args.output,
                generate_audio_flag=(not args.no_audio)
            )
        except Exception as e:
            print(f"Error during Anki card generation: {e}")
            sys.exit(1)

    # 5. Clean up temporary file if created
    if use_groq and input_file_for_anki != args.input and not args.keep_groq_temp:
        try:
            os.remove(input_file_for_anki)
            print(f"Cleaned up temporary file: {input_file_for_anki}")
        except Exception as e:
            print(f"Failed to clean up temporary file: {e}")
    elif use_groq and args.keep_groq_temp:
        print(f"Kept temporary Groq processed file: {input_file_for_anki}")

    print("\n--- Anki Card Generation Finished ---")


if __name__ == "__main__":
    main()