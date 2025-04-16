"""Main application class orchestrating the Anki card generation process."""

import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Iterator

from . import config
from .word_provider import WordProvider
from .word_processor import WordProcessor

class AnkiGeneratorApp:
    """Orchestrates the overall Anki card generation workflow."""

    def __init__(self, args=None):
        """Initialize the app, optionally with pre-parsed args (for GUI mode).
        
        Args:
            args: Pre-parsed arguments (for GUI mode) or None to parse from command line
        """
        self.args = args
        self.can_generate_images = False
        self.word_provider = None
        self.word_processor = None
        self.successful_count = 0
        self.failed_words = []
        self.output_path: Optional[Path] = None
        self.file_mode: Optional[str] = None
        self._output_file_handle = None
        self.input_words = []  # For GUI mode to bypass file input

    def _parse_arguments(self):
        """Parses command-line arguments. (Moved from cli.py)"""
        # Skip if args were already provided (GUI mode)
        if self.args:
            return

        parser = argparse.ArgumentParser(description="Generate Anki cards from a list of German words.")

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
            "--target-language",
            type=str,
            default="english",
            help="Target language for translations (english, french, arabic, etc.)"
        )
        parser.add_argument(
            "--shuffle",
            action="store_true",
            default=True,
            help="Shuffle the input words (default: True)"
        )
        self.args = parser.parse_args()

    def setup(self, input_words=None):
        """Setup the application (for both CLI and GUI modes).
        
        Args:
            input_words: Optional list of words (for GUI mode)
        """
        # Parse arguments if not provided (CLI mode)
        if not self.args:
            self._parse_arguments()
            
        # Store direct input words (for GUI mode)
        if input_words:
            self.input_words = input_words.copy()
            # Print the provided words for debugging
            print(f"\n--- Using {len(self.input_words)} provided words ---")

        # Setup config and check prerequisites
        config.setup_config(self.args)
        prereqs_ok, self.can_generate_images = config.check_prerequisites(self.args)
        if not prereqs_ok:
            print("Prerequisite check failed. Exiting.")
            sys.exit(1)

        # Initialize output file path and mode from args if not already set
        if self.args and hasattr(self.args, 'output') and self.args.output:
            self.output_path = self.args.output
            
            # Only use WordProvider for file-based input mode
            if not self.input_words and hasattr(self.args, 'input') and self.args.input:
                self.word_provider = WordProvider(self.args.input, self.args.output)
                self.file_mode = self.word_provider.get_file_mode()
            else:
                # For GUI mode, always use write mode (assumes GUI handles file overwrite warnings)
                self.file_mode = 'w'
                # Make sure the output directory exists
                if self.output_path:
                    self.output_path.parent.mkdir(parents=True, exist_ok=True)
                    print(f"\n--- Output file '{self.output_path}' will be created/overwritten ---")
        
        print(f"\n--- App Setup: Output path set to {self.output_path}, mode '{self.file_mode}' ---")
        
        # Initialize word processor
        self.word_processor = WordProcessor(self.args, self.can_generate_images)

    def get_total_words(self) -> int:
        """Return the total number of words to process.
        
        Returns:
            int: Total number of words to process
        """
        if self.input_words:
            # Use direct input words if provided (GUI mode)
            return len(self.input_words)
        elif self.word_provider:
            # Use WordProvider if available (CLI mode)
            return len(self.word_provider)
        return 0

    def get_processed_count(self) -> int:
        """Return the number of successfully processed words.
        
        Returns:
            int: Number of successfully processed words
        """
        return self.successful_count

    def run_processing_loop_iterator(self) -> Iterator[Dict[str, Any]]:
        """Generator-based processing loop, yields status updates.
        
        This is used by the GUI to show progress.
        
        Yields:
            Dict with status updates containing type and message
        """
        if not self.word_processor:
            yield {"type": "error", "message": "Word Processor not initialized. Call setup() first."}
            return
            
        # Get words from either direct input or WordProvider
        if self.input_words:
            words_iterator = iter(self.input_words)
            total_words = len(self.input_words)
        elif self.word_provider:
            words_iterator = self.word_provider.get_words()
            total_words = len(self.word_provider)
        else:
            yield {"type": "error", "message": "No words to process. Check input file or provided words."}
            return

        if total_words == 0:
            yield {"type": "log", "message": "No words need processing."}
            return

        yield {"type": "log", "message": f"--- Starting Processing Loop for {total_words} Words ---"}
        
        if config.ANKI_MEDIA_DIR:
            yield {"type": "log", "message": f"Media will be copied to: {config.ANKI_MEDIA_DIR}"}
        else:
            yield {"type": "log", "message": "Anki media path not set. Media files will not be copied."}

        try:
            with self._managed_output_file():
                for i, word in enumerate(words_iterator):
                    yield {"type": "log", "message": f"Processing word: {word}"}
                    processed_line = self.word_processor.process_word(word)
                    
                    if processed_line is not None:
                        self._write_output_line(processed_line)
                        self.successful_count += 1
                        yield {"type": "log", "message": f"Successfully processed '{word}'"}
                    else:
                        self.failed_words.append(word)
                        yield {"type": "log", "message": f"Failed to process '{word}'"}
                    
                    # Update progress
                    yield {"type": "progress", "processed": i + 1, "total": total_words}
                    
        except Exception as e:
            error_msg = f"An unexpected error occurred during processing: {e}"
            print(f"\n{error_msg}")
            yield {"type": "error", "message": error_msg}

    @contextmanager
    def _managed_output_file(self):
        """Context manager to handle opening and closing the output file."""
        if not self.output_path or not self.file_mode:
            raise RuntimeError("Output path or file mode not set during setup.")
        try:
            print(f"Opening output file: {self.output_path} (mode: '{self.file_mode}')")
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._output_file_handle = open(self.output_path, self.file_mode, encoding='utf-8')
            yield
        except IOError as e:
            print(f"\nError: Could not open or write to output file {self.output_path}: {e}")
            sys.exit(1)
        finally:
            if self._output_file_handle:
                self._output_file_handle.close()
                self._output_file_handle = None
                print(f"Closed output file: {self.output_path}")

    def _write_output_line(self, line: str):
        """Writes a single line to the currently open output file."""
        if not self._output_file_handle:
            raise IOError("Output file is not open for writing. Use 'with self._managed_output_file():'")
        self._output_file_handle.write(line + '\n')

    def _run_processing_loop(self):
        """Iterates through words, processes them, and writes output."""
        # For CLI mode - using the traditional loop with tqdm
        if not self.word_processor:
            raise RuntimeError("Word Processor not initialized. Call setup() first.")

        # Get words from either direct input or WordProvider
        if self.input_words:
            words_iterator = iter(self.input_words)
            total_words = len(self.input_words)
        elif self.word_provider:
            words_iterator = self.word_provider.get_words()
            total_words = len(self.word_provider)
        else:
            print("\nNo words to process.")
            return

        if total_words == 0:
            print("\nNo words need processing.")
            return

        print(f"\n--- Starting Processing Loop for {total_words} Words ---")
        if config.ANKI_MEDIA_DIR:
            print(f"Media will be copied to: {config.ANKI_MEDIA_DIR}")
        else:
            print("Anki media path not set. Media files will not be copied.")

        try:
            with self._managed_output_file():
                for word in tqdm(words_iterator, total=total_words, desc="Processing words"):
                    processed_line = self.word_processor.process_word(word)
                    if processed_line is not None:
                        self._write_output_line(processed_line)
                        self.successful_count += 1
                    else:
                        self.failed_words.append(word)
        except Exception as e:
            print(f"\nAn unexpected error occurred during the main processing loop: {e}")

    def get_summary(self) -> str:
        """Get a summary of the generation process.
        
        Returns:
            str: Summary of the generation process
        """
        summary = []
        summary.append(f"Successfully processed: {self.successful_count} words.")
        if self.failed_words:
            summary.append(f"Failed to process: {len(self.failed_words)} words: {', '.join(self.failed_words)}")
        return "\n".join(summary)

    def _print_summary(self):
        """Prints a final summary of the generation process."""
        print(f"\n--- Anki Card Generation Process Completed --- ")
        if hasattr(self.args, 'output') and self.args.output:
            print(f"Output file: {self.args.output}")
        if config.ANKI_MEDIA_DIR:
            print(f"Media files saved in {config.AUDIO_OUTPUT_DIR}, {config.IMAGE_OUTPUT_DIR} and copied to {config.ANKI_MEDIA_DIR}")
        else:
            print(f"Media files saved in {config.AUDIO_OUTPUT_DIR}, {config.IMAGE_OUTPUT_DIR}.")
            print("Anki media path not specified, files were not copied.")
        
        # Print the same summary that get_summary would return
        print(self.get_summary())

    def run(self):
        """Executes the entire Anki card generation process for CLI mode."""
        self.setup()
        self._run_processing_loop()
        self._print_summary()
