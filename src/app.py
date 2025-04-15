"""Main application class orchestrating the Anki card generation process."""

import sys
import argparse
from pathlib import Path
from tqdm import tqdm
from contextlib import contextmanager
from typing import Optional

from . import config
from .word_provider import WordProvider
from .word_processor import WordProcessor

class AnkiGeneratorApp:
    """Orchestrates the overall Anki card generation workflow."""

    def __init__(self):
        self.args = None
        self.can_generate_images = False
        self.word_provider = None
        self.word_processor = None
        self.successful_count = 0
        self.failed_words = []
        self.output_path: Optional[Path] = None
        self.file_mode: Optional[str] = None
        self._output_file_handle = None

    def _parse_arguments(self):
        """Parses command-line arguments. (Moved from cli.py)"""
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
        self.args = parser.parse_args()

    def _setup(self):
        """Handles argument parsing, config loading, and prerequisite checks."""
        self._parse_arguments()
        config.setup_config(self.args)
        prereqs_ok, self.can_generate_images = config.check_prerequisites(self.args)
        if not prereqs_ok:
            print("Prerequisite check failed. Exiting.")
            sys.exit(1)

        self.word_provider = WordProvider(self.args.input, self.args.output)

        self.output_path = self.args.output
        self.file_mode = self.word_provider.get_file_mode()
        print(f"\n--- App Setup: Output path set to {self.output_path}, mode '{self.file_mode}' ---")

        self.word_processor = WordProcessor(self.args, self.can_generate_images)

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
        if not self.word_provider or not self.word_processor:
             raise RuntimeError("Word Provider or Processor not initialized. Call _setup() first.")

        words_iterator = self.word_provider.get_words()
        total_words = len(self.word_provider)

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

    def _print_summary(self):
        """Prints a final summary of the generation process."""
        print(f"\n--- Anki Card Generation Process Completed --- ")
        print(f"Output file: {self.args.output}")
        if config.ANKI_MEDIA_DIR:
            print(f"Media files saved in {config.AUDIO_OUTPUT_DIR}, {config.IMAGE_OUTPUT_DIR} and copied to {config.ANKI_MEDIA_DIR}")
        else:
            print(f"Media files saved in {config.AUDIO_OUTPUT_DIR}, {config.IMAGE_OUTPUT_DIR}.")
            print("Anki media path not specified, files were not copied.")
        print(f"Successfully processed: {self.successful_count} words.")
        if self.failed_words:
            print(f"Failed to process: {len(self.failed_words)} words: {self.failed_words}")

    def run(self):
        """Executes the entire Anki card generation process."""
        self._setup()
        self._run_processing_loop()
        self._print_summary()
