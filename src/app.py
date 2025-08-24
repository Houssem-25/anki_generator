"""
Main entry point for the Anki Card Generator.
Supports both CLI and GUI modes.
"""

import sys
import argparse
from pathlib import Path
from typing import List

from config import get_config, get_processing_options, validate_config, setup_directories
from processor import create_processor
from structures import ProcessingOptions


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate Anki cards from German words using AI services."
    )
    
    parser.add_argument(
        "-i", "--input",
        type=Path,
        help="Path to input file containing German words (one per line)"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Path to output Anki file (.txt format)"
    )
    
    parser.add_argument(
        "--target-language",
        type=str,
        default="english",
        help="Target language for translations (default: english)"
    )
    
    parser.add_argument(
        "--no-audio",
        action="store_true",
        help="Skip audio generation"
    )
    
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Skip image generation"
    )
    
    parser.add_argument(
        "--anki-media-path",
        type=Path,
        help="Path to Anki media directory for automatic file copying"
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch GUI interface"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    return parser.parse_args()


def read_words_from_file(file_path: Path) -> List[str]:
    """Read words from input file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f if line.strip()]
        
        print(f"Read {len(words)} words from {file_path}")
        return words
        
    except FileNotFoundError:
        print(f"Error: Input file not found: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)


def process_words_cli(options: ProcessingOptions, words: List[str]):
    """Process words in CLI mode."""
    from tqdm import tqdm
    
    # Create processor
    processor = create_processor(options)
    
    # Process words with progress bar
    results = []
    for word in tqdm(words, desc="Processing words"):
        result = processor.process_word(word)
        results.append(result)
        
        # Update stats
        if result.success:
            processor.stats.processed_words += 1
        else:
            processor.stats.failed_words += 1
            processor.stats.failed_word_list.append(word)
    
    # Save results
    config = get_config()
    processor.save_cards_to_file(results, config.output_file)
    
    # Print summary
    processor.print_summary()


def process_words_gui(options: ProcessingOptions, words: List[str], 
                     progress_callback=None):
    """Process words in GUI mode."""
    # Create processor
    processor = create_processor(options)
    
    # Process words with progress callback
    results = processor.process_words(words, progress_callback)
    
    # Save results
    config = get_config()
    processor.save_cards_to_file(results, config.output_file)
    
    return processor.get_stats()


def run_cli():
    """Run the application in CLI mode."""
    args = parse_arguments()
    
    # Validate configuration
    errors = validate_config()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    # Setup directories
    setup_directories()
    
    # Get configuration
    config = get_config()
    
    # Override config with command line arguments
    if args.input:
        config.input_file = args.input
    if args.output:
        config.output_file = args.output
    
    # Create processing options
    options = ProcessingOptions(
        target_language=args.target_language,
        generate_audio=not args.no_audio,
        generate_images=not args.no_image,
        anki_media_path=args.anki_media_path,
        debug_mode=args.debug
    )
    
    # Read words from file
    words = read_words_from_file(config.input_file)
    
    if not words:
        print("No words to process.")
        return
    
    # Process words
    process_words_cli(options, words)


def run_gui():
    """Run the application in GUI mode."""
    try:
        from gui import run_gui_application
        run_gui_application()
    except ImportError as e:
        print(f"Error: GUI dependencies not available: {e}")
        print("Please install PyQt5 to use the GUI: pip install PyQt5")
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_arguments()
    
    if args.gui:
        run_gui()
    else:
        run_cli()


if __name__ == "__main__":
    main()
