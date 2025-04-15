import time
import base64
import shutil
import re
import groq
from typing import Optional, Dict, Any, Tuple

from . import config
from . import llm_generator
from . import image_generator
from . import audio_generator

# ... (constants remain the same) ...
MAX_GROQ_RETRIES = 50
DEFAULT_GROQ_RETRY_DELAY_SECONDS = 60.0

class WordProcessor:
    # ... (__init__, process_word, _parse_retry_after, _handle_groq_error, _generate_text, _format_base_line, _generate_image remain the same) ...
    def __init__(self, args: Any, can_generate_images: bool):
        """Initializes the WordProcessor.

        Args:
            args: Parsed command-line arguments (needed for flags like --no-audio).
            can_generate_images: Flag indicating if image generation is possible.
        """
        self.args = args
        self.can_generate_images = can_generate_images
        print("--- Initializing WordProcessor ---")

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use as a filename."""
        # Replace spaces and special characters with underscores
        # Keep umlauts and other German characters
        sanitized = text.strip()
        sanitized = ''.join(c if c.isalnum() or c in 'äöüÄÖÜß' else '_' for c in sanitized)
        return sanitized

    def process_word(self, word: str) -> Optional[str]:
        """Processes a single word and returns the formatted Anki line, or None on failure."""
        print(f"\nProcessing word: {word}")

        # 1. Text Generation (Groq)
        item = self._generate_text(word)
        if item is None:
            print(f"  Skipping '{word}' due to failure in text generation.")
            return None

        # 2. Format Base Line
        base_line = self._format_base_line(item)
        if base_line is None:
            print(f"  Skipping '{word}' due to failure in formatting.")
            return None

        # Split line for tag insertion
        try:
            english_part, german_part = base_line.split(';', 1)
        except ValueError:
            print(f"  Warning: Formatted line for '{word}' has unexpected format: \"{base_line}\". Using as is.")
            english_part = base_line
            german_part = ""

        # 3. Image Generation (Optional)
        img_tag = self._generate_image(word, item)

        # 4. Audio Generation (Optional)
        sound_tag = self._generate_audio(word)

        # 5. Construct Final Line
        final_line = f"{img_tag}{english_part};{sound_tag}{german_part}"
        print(f"  Successfully generated components for '{word}'.")
        return final_line

    # --- Private Helper Methods ---

    def _parse_retry_after(self, error_message: str) -> float:
        """Parses the delay time from Groq rate limit error messages."""
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
            return DEFAULT_GROQ_RETRY_DELAY_SECONDS

    def _handle_groq_error(self, error: Exception, word: str, retries: int) -> Tuple[bool, float, int]:
        """Handle Groq API errors with exponential backoff."""
        error_name = error.__class__.__name__
        error_detail = str(getattr(error, 'detail', str(error)))
        
        # Check if we've hit the retry limit
        if retries >= self.MAX_GROQ_RETRIES:
            print(f"  Max retries ({self.MAX_GROQ_RETRIES}) reached for word '{word}'. Skipping.")
            return False, 0, retries
        
        # Rate limit errors get a fixed delay
        if error_name == "RateLimitError":
            print(f"  Unexpected error during Groq call for '{word}': {error}. Retrying after fixed delay...")
            return True, 31.0, retries + 1  # Fixed 31-second delay for rate limits
        
        # Other errors get exponential backoff
        delay = min(2 ** retries, self.MAX_BACKOFF_DELAY)
        print(f"  Unexpected error during Groq call for '{word}': {error}. Retrying with exponential backoff...")
        return True, delay, retries + 1

    def _generate_text(self, word: str) -> Optional[Dict[str, Any]]:
        """Generates text data using the LLM generator with retry logic."""
        retries = 0
        while True:
            try:
                # Use the renamed module
                processed_data_list = llm_generator.process_german_words([word])
                if not processed_data_list:
                    print(f"  Warning: LLM processing returned no data for '{word}'.")
                    return None
                
                item = processed_data_list[0]
                if not item.get("word_translation"):
                    print(f"  Warning: LLM returned incomplete data for '{word}' (missing translation). Skipping.")
                    return None
                
                return item # Success

            except Exception as e:
                # Update error messages if needed, _handle_groq_error still checks groq types
                should_retry, delay, retries = self._handle_groq_error(e, word, retries)
                if should_retry:
                    print(f"    Waiting {delay:.2f}s before retrying LLM...") # Update log message
                    time.sleep(delay)
                else:
                    return None

    def _format_base_line(self, item: Dict[str, Any]) -> Optional[str]:
        """Formats the base Anki line from the processed LLM data."""
        word = item.get('word', 'unknown word')
        try:
            # Use the renamed module
            formatted_lines = llm_generator.format_for_anki_import([item])
            if formatted_lines:
                return formatted_lines[0]
            else:
                print(f"  Error: Could not format LLM data for '{word}'.")
                return None
        except Exception as e:
            print(f"  Error formatting LLM data for '{word}': {e}")
            return None

    def _generate_image(self, word: str, item: Dict[str, Any]) -> str:
        """Generates image, saves it, copies, and returns the image tag."""
        if not self.can_generate_images:
            return ""

        print(f"  Generating image for '{word}'...")
        word_translation = item.get('word_translation', word)
        english_sentence = item.get('translation', '')
        img_tag = ""

        try:
            base64_image = image_generator.generate_image_for_prompt(
                word_translation=word_translation,
                english_sentence=english_sentence,
                account_id=config.CLOUDFLARE_ACCOUNT_ID,
                api_token=config.CLOUDFLARE_API_TOKEN
            )

            if base64_image:
                safe_filename_base = self._sanitize_filename(word)
                safe_filename_with_ext = safe_filename_base + ".png"
                image_path = config.IMAGE_OUTPUT_DIR / safe_filename_with_ext

                # Ensure directory exists before saving
                config.IMAGE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

                # Save the image
                try:
                    image_bytes = base64.b64decode(base64_image)
                    with open(image_path, 'wb') as img_file:
                        img_file.write(image_bytes)
                    print(f"    Image saved to: {image_path}")
                    img_tag = f'<img src="{safe_filename_with_ext}"><br>'

                    # Copy image to Anki media directory if specified
                    if config.ANKI_MEDIA_DIR:
                        config.ANKI_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
                        try:
                            anki_media_image_path = config.ANKI_MEDIA_DIR / safe_filename_with_ext
                            shutil.copy2(image_path, anki_media_image_path)
                            print(f"    Image copied to Anki media: {anki_media_image_path}")
                        except Exception as copy_e:
                            print(f"    Warning: Failed to copy image '{safe_filename_with_ext}' to Anki media: {copy_e}")

                except Exception as img_save_e:
                    print(f"    Error saving image for '{word}': {img_save_e}")
                    img_tag = ""
            else:
                print(f"    Failed to generate image for '{word}'. No image data received.")

        except Exception as img_gen_e:
            print(f"    Error during image generation request for '{word}': {img_gen_e}")

        return img_tag

    def _generate_audio(self, word: str) -> str:
        """Generates audio using the audio generator module."""
        if self.args.no_audio:
            return ""

        print(f"  Generating audio for '{word}'...")
        sound_tag = ""
        try:
            # Sanitize filename here
            safe_filename_base = self._sanitize_filename(word)
            
            # Ensure output directories exist (can be done here or in audio_generator)
            # config.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            # if config.ANKI_MEDIA_DIR:
            #      config.ANKI_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

            # Pass original word and sanitized base filename
            sound_tag = audio_generator.generate_audio(word, safe_filename_base)
            if sound_tag:
                print(f"    Audio tag generated: {sound_tag}")
            else:
                print(f"    Warning: Audio generation for '{word}' did not return a sound tag.")
        except Exception as audio_e:
            print(f"    Error generating audio for '{word}': {audio_e}")
        
        return sound_tag if sound_tag else ""
