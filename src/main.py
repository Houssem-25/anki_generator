import argparse
import sys
import os
from pathlib import Path
# import subprocess # Removed - Moved to image_generator
# import json # Removed - Moved to image_generator
import base64 # Needed for decoding image data before saving
from dotenv import load_dotenv # Import load_dotenv
import shutil # Added for file copying
from tqdm import tqdm # Import tqdm for progress bars - RE-ADDED
import random # Import the random module
import time  # Import time for sleep
import re    # Import re for parsing delay
import groq  # Import groq to catch specific API errors

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path to allow absolute imports from src
# This makes the script runnable as 'python src/main.py' from the root directory
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root.parent))

from src import config
# from src import nlp_utils # Removed - Unused
from src import anki_generator
from src import groq_generator
from src import image_generator # Import the new module
from src import audio # Import audio module directly
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
        help="Path to your Anki profile's collection.media folder. If provided, audio/image files will be copied here."
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Skip image generation using Cloudflare AI."
    )
    parser.add_argument(
        "--keep-groq-temp",
        action="store_true",
        help="Keep the temporary Groq output file."
    )

    args = parser.parse_args()

    # --- Configuration Update ---
    # Set the global ANKI_MEDIA_DIR in the config module if the argument is provided
    if args.anki_media_path:
        print(f"Using specified Anki media path: {args.anki_media_path}")
        # Ensure the path exists before setting it in config
        if not args.anki_media_path.is_dir():
            print(f"Warning: Anki media path provided does not exist or is not a directory: {args.anki_media_path}")
            print("Audio/Image files will be generated but not copied.")
            config.ANKI_MEDIA_DIR = None # Keep it None if path is invalid
        else:
            config.ANKI_MEDIA_DIR = args.anki_media_path # Update global config
    else:
        config.ANKI_MEDIA_DIR = None # Explicitly None if not provided

    # --- Prerequisite Checks ---
    # 1. Groq API Key
    if "GROQ_API_KEY" not in os.environ or not os.environ["GROQ_API_KEY"]:
        print("\nError: Groq API key not found or empty (GROQ_API_KEY).")
        sys.exit(1)

    # 2. Cloudflare Credentials (Optional for Images)
    cloudflare_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    cloudflare_api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    can_generate_images = False
    if not args.no_image:
        if cloudflare_account_id and cloudflare_api_token:
            print("\n--- Cloudflare credentials found. Image generation enabled. ---")
            can_generate_images = True
        else:
            print("\nWarning: Cloudflare credentials missing. Skipping image generation.")
            print("Set CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN to enable images.")

    # --- Read Input Words ---
    print("\n--- Reading Input Words ---")
    original_words = []
    try:
        with open(args.input, 'r', encoding='utf-8') as infile:
            original_words = [line.strip() for line in infile.readlines() if line.strip()]
        if not original_words:
            print(f"Error: Input file {args.input} is empty.")
            sys.exit(1)
        print(f"Found {len(original_words)} words in {args.input}")
    except FileNotFoundError:
        print(f"Error: Input file not found at {args.input}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file {args.input}: {e}")
        sys.exit(1)

    # --- Shuffle Words (New Step) ---
    print("\n--- Shuffling Words ---")
    random.shuffle(original_words)
    print("Words shuffled successfully.")

    # --- Check for Existing Output and Determine Words to Process ---
    processed_words_set = set()
    words_to_process = []
    file_mode = 'w' # Default to write mode
    if args.output.exists() and args.output.stat().st_size > 0:
        print(f"\n--- Output file '{args.output}' exists. Attempting to resume. ---")
        try:
            with open(args.output, 'r', encoding='utf-8') as infile:
                for line in infile:
                    # Extract word from sound tag: [sound:WORD.mp3]
                    match = re.search(r'\[sound:(.*?)\.mp3\]', line)
                    if match:
                        processed_word = match.group(1)
                        processed_words_set.add(processed_word)
            print(f"Found {len(processed_words_set)} already processed words in output file.")
            file_mode = 'a' # Switch to append mode
        except Exception as e:
            print(f"Warning: Could not read or parse existing output file '{args.output}': {e}")
            print("Proceeding in write mode (will overwrite existing file).")
            file_mode = 'w'
            processed_words_set.clear() # Ensure we process all words if reading failed

    # Filter the original list based on processed words
    words_to_process = [word for word in original_words if word not in processed_words_set]

    if file_mode == 'a':
        print(f"\nResuming generation. {len(words_to_process)} words remaining to process.")
    else:
        print(f"\nStarting fresh generation. {len(words_to_process)} words to process.")

    if not words_to_process:
        print("\nAll words from the input file are already present in the output file. Nothing to do.")
        sys.exit(0)

    # --- Ensure Output Directories Exist ---
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if can_generate_images:
        config.IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.no_audio:
        config.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # Ensure audio dir exists

    # --- Process Words Sequentially ---
    print(f"\n--- Processing {len(words_to_process)} Words Sequentially --- ")
    print(f"Outputting to: {args.output}")
    if config.ANKI_MEDIA_DIR:
        print(f"Copying media to: {config.ANKI_MEDIA_DIR}")

    # Open the output file once before the loop
    try:
        # Use the determined file mode ('w' or 'a')
        with open(args.output, file_mode, encoding='utf-8') as outfile:
            # Loop through the words that still need processing
            for word in tqdm(words_to_process, desc="Processing words"):
                print(f"\nProcessing word: {word}")
                # Reset state for each word
                final_line = None
                item = None
                processed_data_single = []

                # --- Constants for Retry Logic ---
                MAX_RETRIES = 50
                DEFAULT_RETRY_DELAY_SECONDS = 60.0

                def parse_retry_after(error_message: str) -> float:
                    # Try to find the specific delay pattern
                    match = re.search(r'try again in (?:(\d+)m)?(\d{1,3}(?:\.\d+)?)s', error_message)
                    if match:
                        minutes = int(match.group(1)) if match.group(1) else 0
                        seconds = float(match.group(2))
                        calculated_delay = minutes * 60 + seconds
                        # Add a small buffer (e.g., 1 second) to be safe
                        return max(1.0, calculated_delay + 1.0)
                    else:
                        # Fallback if parsing fails
                        return DEFAULT_RETRY_DELAY_SECONDS

                # 1. Text Generation (Groq) with Retry Logic
                retries = 0
                while retries < MAX_RETRIES:
                    try:
                        processed_data_single = groq_generator.process_german_words([word])
                        if processed_data_single and len(processed_data_single) > 0:
                            item = processed_data_single[0]
                            if not item.get("word_translation"): # Basic check
                                print(f"  Warning: Groq returned limited data for '{word}'.")
                        elif not processed_data_single:
                            print(f"  Warning: Groq processing returned no data for '{word}'.")
                            item = {} # Ensure item is a dict
                        else:
                             print(f"  Warning: Unexpected state after Groq processing for '{word}'.")
                             item = {}
                        # Success! Break the retry loop
                        break

                    except groq.RateLimitError as e: # Handle Rate Limit specifically
                        retries += 1 # Consume a retry attempt ONLY for rate limits
                        if retries >= MAX_RETRIES:
                            print(f"  Error: Max retries ({MAX_RETRIES}) reached for '{word}' due to rate limit. Skipping.")
                            item = None # Signal failure to proceed for this word
                            break # Exit retry loop for this word

                        error_detail = str(e)
                        delay = parse_retry_after(error_detail)
                        print(f"  Rate limit hit for '{word}'. Retrying in {delay:.2f} seconds... (Attempt {retries}/{MAX_RETRIES})")
                        time.sleep(delay)
                        # Continue to the next iteration of the while loop (retrying the same word)
                        continue

                    except groq.APIError as e: # Handle *other* Groq API errors by retrying indefinitely
                        print(f"  Error processing '{word}' with Groq API: {e}. Retrying after delay...")
                        time.sleep(15) # Wait for a fixed delay (e.g., 15 seconds)
                        # Continue to the next iteration of the while loop (retrying the same word)
                        # DO NOT increment retries or break
                        continue

                    except Exception as e: # Handle *other* unexpected errors by retrying indefinitely
                        print(f"  Unexpected error processing '{word}' with Groq: {e}. Retrying after delay...")
                        time.sleep(15) # Wait for a fixed delay (e.g., 15 seconds)
                        # Continue to the next iteration of the while loop (retrying the same word)
                        # DO NOT increment retries or break
                        continue

                # If item is None after the loop, Groq failed definitively (max retries *for rate limit*)
                if item is None:
                    continue # Skip to the next word

                # Add a check here if item is {} (empty dict from clean return but no data)
                if not item: # Checks if dict is empty ({})
                    print(f"  Skipping '{word}' due to no valid data from Groq after processing.")
                    continue

                # 2. Format Base Line (using Groq's formatter)
                base_line = ""
                try:
                    formatted_lines_single = groq_generator.format_for_anki_import([item])
                    if formatted_lines_single:
                        base_line = formatted_lines_single[0]
                    else:
                         print(f"  Error: Could not format Groq data for '{word}'. Skipping this word.")
                         continue
                except Exception as e:
                    print(f"  Error formatting Groq data for '{word}': {e}. Skipping this word.")
                    continue

                # Split into English and German parts for tag insertion
                try:
                    english_part, german_part = base_line.split(';', 1)
                except ValueError:
                     print(f"  Warning: Formatted line for '{word}' has unexpected format: \"{base_line}\". Using as is, tags might be misplaced.")
                     english_part = base_line # Assign whole line to english part as fallback
                     german_part = ""

                img_tag = ""
                sound_tag = ""

                # 3. Image Generation (Optional)
                if can_generate_images:
                    print(f"  Generating image for '{word}'...")
                    word_translation = item.get('word_translation', word) # Use original word as fallback prompt
                    english_sentence = item.get('translation', '')
                    try:
                        base64_image = image_generator.generate_image_for_prompt(
                            word_translation=word_translation,
                            english_sentence=english_sentence,
                            account_id=cloudflare_account_id,
                            api_token=cloudflare_api_token
                        )

                        if base64_image:
                            safe_filename = "".join(c if c.isalnum() else '_' for c in word) + ".png"
                            image_path = config.IMAGE_OUTPUT_DIR / safe_filename

                            # Save the image
                            try:
                                image_bytes = base64.b64decode(base64_image)
                                with open(image_path, 'wb') as img_file:
                                    img_file.write(image_bytes)
                                print(f"    Image saved to: {image_path}")
                                img_tag = f'<img src="{safe_filename}"><br>' # Add line break after image

                                # Copy image to Anki media directory if specified
                                if config.ANKI_MEDIA_DIR:
                                    try:
                                        anki_media_image_path = config.ANKI_MEDIA_DIR / safe_filename
                                        shutil.copy2(image_path, anki_media_image_path)
                                        print(f"    Image copied to Anki media: {anki_media_image_path}")
                                    except Exception as copy_e:
                                        print(f"    Warning: Failed to copy image '{safe_filename}' to Anki media: {copy_e}")

                            except Exception as img_save_e:
                                print(f"    Error saving image for '{word}': {img_save_e}")
                                img_tag = "" # Clear tag if saving failed
                        else:
                            print(f"    Failed to generate image for '{word}'. No image data received.")

                    except Exception as img_gen_e:
                        print(f"    Error during image generation request for '{word}': {img_gen_e}")

                # 4. Audio Generation (Optional)
                if not args.no_audio:
                    print(f"  Generating audio for '{word}'...")
                    try:
                        # Assuming audio.generate_audio handles saving and copying, returning the tag
                        sound_tag = audio.generate_audio(word) # Use the original word
                        if sound_tag:
                            print(f"    Audio tag generated: {sound_tag}")
                        else:
                            print(f"    Warning: Audio generation for '{word}' did not return a sound tag.")
                    except Exception as audio_e:
                        print(f"    Error generating audio for '{word}': {audio_e}")

                # 5. Construct Final Line and Write to File
                final_line = f"{img_tag}{english_part};{sound_tag}{german_part}"
                outfile.write(final_line + '\n')
                print(f"  Successfully processed and wrote entry for '{word}'.")

    except IOError as e:
        print(f"\nError: Could not write to output file {args.output}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred during processing: {e}")
        # Consider adding more specific error handling or logging here
        sys.exit(1)

    print("\n--- Anki Card Generation Finished ---")
    print(f"Output file: {args.output}")
    if config.ANKI_MEDIA_DIR:
        print(f"Media files (audio/images) generated in {config.AUDIO_OUTPUT_DIR}, {config.IMAGE_OUTPUT_DIR} and copied to {config.ANKI_MEDIA_DIR}")
    else:
         print(f"Media files (audio/images) generated in {config.AUDIO_OUTPUT_DIR}, {config.IMAGE_OUTPUT_DIR}. Anki media path not specified for copying.")

if __name__ == "__main__":
    main()