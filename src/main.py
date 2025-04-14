import argparse
import sys
import os
from pathlib import Path
import subprocess # For calling curl
import json # For parsing curl response
import base64 # For decoding image data
from dotenv import load_dotenv # Import load_dotenv
import shutil # Added for file copying
from tqdm import tqdm # Import tqdm for progress bars

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
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Skip image generation using Cloudflare AI."
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

    # --- Cloudflare Image Gen Setup ---
    cloudflare_account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    cloudflare_api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    can_generate_images = False
    if not args.no_image:
        if cloudflare_account_id and cloudflare_api_token:
            print("\n--- Cloudflare credentials found. Image generation enabled. ---")
            can_generate_images = True
        else:
            print("\nWarning: Cloudflare credentials (CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN) not found in environment.")
            print("Skipping image generation. Use --no-image to suppress this warning.")

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
    processed_data = [] # Initialize processed_data as well
    try:
        # Call process_words_file without the output_file_path argument
        # Correctly unpack both return values
        formatted_lines, processed_data = groq_generator.process_words_file(
            input_file_path=args.input
        )

        if not formatted_lines:
            print("Error: No data was processed by Groq. Check input file or API connection.")
            sys.exit(1)

    except Exception as e:
        print(f"\nError during Groq API processing: {e}")
        print("Please check your input file, Groq API key, and network connection.")
        sys.exit(1) # Exit on Groq processing error

    # --- Image Generation (Optional) ---
    if can_generate_images:
        print("\n--- Generating Images (may take some time) ---")
        # Ensure the image output directory exists
        config.IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        updated_formatted_lines = []
        # Add tqdm progress bar
        for i, item in enumerate(tqdm(processed_data, desc="Generating images", unit="image")):
            original_line = formatted_lines[i]
            english_part, german_part = original_line.split(';', 1)

            # Construct the new prompt using the English translation and example sentence
            word_translation = item.get('word_translation', '')
            english_sentence = item.get('translation', '') # Get the English example sentence
            prompt = f"""
                        Create a vibrant, child-friendly flashcard illustration for the word '{word_translation}'.
                        SCENE DETAILS:
                        - Illustrate this example sentence: '{english_sentence}'
                        - Just use image from the internet
                        - Create a clear, engaging scene that instantly communicates the word's meaning
                        - Include characters demonstrating the word through their actions/interactions
                        - Maintain a clean, uncluttered background to help with focus and memory retention

                        EMOTIONAL IMPACT:
                        - Feature one strong, age-appropriate emotion that reinforces the word's meaning
                        - Use exaggerated facial expressions and dynamic poses for memorable impact
                        - Ensure the emotional tone (joy, surprise, curiosity, etc.) connects directly to the word

                        VISUAL STYLE (select ONE):
                        - Storybook Adventure: Warm colors, soft edges, whimsical elements
                        - Anime-Inspired: Expressive eyes, dynamic poses, bold energy
                        - Ghibli Wonder: Natural elements, thoughtful details, gentle magic
                        - Modern Cartoon: Clean lines, vibrant colors, contemporary feel
                        - Stylized Realism: Simplified but recognizable real-world elements

                        LEARNING EFFECTIVENESS:
                        - Position the key concept centrally with strong visual hierarchy
                        - Include 1-2 distinctive visual elements that serve as memory anchors
                        - Use color psychology to enhance emotional connection
                        - Create a visual that works effectively at flashcard size
                    """
            print(f"  Generating image for: '{item.get('word', '')}' (Prompt based on: '{word_translation}' / Sentence: '{english_sentence}')...")
            base64_image = generate_image_for_prompt(prompt, cloudflare_account_id, cloudflare_api_token)

            if base64_image:
                # Create a safe filename (e.g., based on German word)
                safe_filename = "".join(c if c.isalnum() else '_' for c in item.get('word', '')) + ".png"
                image_path = config.IMAGE_OUTPUT_DIR / safe_filename
                img_tag = f'<img src="{safe_filename}">' # Use filename in img tag

                # Save the image to a file
                try:
                    image_bytes = base64.b64decode(base64_image)
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_bytes)
                    print(f"    Image saved to: {image_path}")

                    # Copy image to Anki media directory if specified
                    if config.ANKI_MEDIA_DIR:
                        try:
                            anki_media_image_path = config.ANKI_MEDIA_DIR / safe_filename
                            shutil.copy2(image_path, anki_media_image_path) # copy2 preserves metadata
                            print(f"    Image copied to Anki media: {anki_media_image_path}")
                        except Exception as copy_e:
                            print(f"    Warning: Failed to copy image to Anki media directory '{config.ANKI_MEDIA_DIR}': {copy_e}")

                except Exception as img_save_e:
                    print(f"    Error saving image for '{item.get('word', '')}': {img_save_e}")
                    img_tag = "" # Don't add image tag if saving failed

                # Prepend image tag to the English part (only if img_tag is not empty)
                if img_tag:
                    updated_line = f"{img_tag}<br>{english_part};{german_part}"
                    updated_formatted_lines.append(updated_line)
                else:
                    updated_formatted_lines.append(original_line) # Use original if saving/tag failed

            else:
                print(f"  Failed to generate image for '{item.get('word', '')}'. Skipping.")
                updated_formatted_lines.append(original_line) # Use original line if image fails
        
        # Use the updated lines for the Anki deck
        formatted_lines = updated_formatted_lines 
    else:
        print("\n--- Skipping Image Generation ---")

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

def generate_image_for_prompt(prompt: str, account_id: str, api_token: str) -> str | None:
    """Generates an image using Cloudflare AI via curl and returns base64 data."""
    api_endpoint = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    data = json.dumps({"prompt": prompt})

    try:
        # Use subprocess.run to execute curl
        # Set timeout to avoid hanging indefinitely (e.g., 60 seconds)
        command = [
            "curl", "-s", "-X", "POST", api_endpoint,
            "-H", f"Authorization: {headers['Authorization']}",
            "-H", f"Content-Type: {headers['Content-Type']}",
            "-d", data
        ]
        process = subprocess.run(
            command, # Use the constructed command list
            capture_output=True,
            text=True, # Get stdout/stderr as strings
            check=True, # Raise CalledProcessError on non-zero exit code
            timeout=60 
        )

        # Parse the JSON response from stdout
        response_json = json.loads(process.stdout)
        
        # Check if image data is present
        if "result" in response_json and "image" in response_json["result"]:
             # Cloudflare seems to wrap the result in a "result" object now
            return response_json["result"]["image"]
        elif "image" in response_json: # Handle direct image response if API changes
            return response_json["image"]
        else:
            print(f"  Error: Unexpected response format from Cloudflare AI: {response_json}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"  Error calling Cloudflare AI (curl failed): {e}")
        print(f"  Stderr: {e.stderr}")
        return None
    except subprocess.TimeoutExpired:
        print(f"  Error: Cloudflare AI request timed out for prompt: '{prompt}'")
        return None
    except json.JSONDecodeError as e:
        print(f"  Error decoding JSON response from Cloudflare AI: {e}")
        print(f"  Raw Response: {process.stdout}")
        return None
    except Exception as e:
        print(f"  An unexpected error occurred during image generation: {e}")
        return None

if __name__ == "__main__":
    main()