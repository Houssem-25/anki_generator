"""Main entry point for the Anki Card Generator application."""

import sys
from pathlib import Path
import os

# Add the project root to the Python path for absolute imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import the main application class
from src.app import AnkiGeneratorApp

def main():
    """Initializes and runs the Anki Generator application."""
    app = AnkiGeneratorApp()
    app.run()

def process_words_for_gui(input_file, output_file, target_language=None, with_images=False, 
                      progress_callback=None, log_callback=None, should_stop_callback=None):
    """Process words for GUI with callbacks for progress updates and stopping.
    
    Args:
        input_file: Path to input file
        output_file: Path to output Anki deck file
        target_language: Optional target language for translation
        with_images: Whether to include images in the cards
        progress_callback: Function to call with progress updates (current, total, current_word)
        log_callback: Function to call with log messages
        should_stop_callback: Function to check if processing should stop
        
    Returns:
        Path to the created Anki deck
    """
    # Log starting message
    if log_callback:
        log_callback(f"Starting processing with target language: {target_language}")
    
    # Read input words
    with open(input_file, 'r', encoding='utf-8') as f:
        words = [line.strip() for line in f.readlines() if line.strip()]
    
    total_words = len(words)
    if log_callback:
        log_callback(f"Found {total_words} words to process")
    
    # Initialize the processor and generator
    processor = WordProcessor(language=target_language if target_language else 'english')
    generator = LLMGenerator(target_language=target_language)
    provider = WordProvider()
    
    # Initialize the deck builder
    if output_file.endswith('.txt'):
        output_path = output_file
    else:
        output_path = output_file + '.txt'
    deck_name = os.path.splitext(os.path.basename(output_path))[0]
    
    if log_callback:
        log_callback(f"Creating deck: {deck_name}")
        
    builder = DeckBuilder(deck_name)
    
    # Process each word
    for i, word in enumerate(words):
        # Check if we should stop
        if should_stop_callback and should_stop_callback():
            if log_callback:
                log_callback("Processing stopped by user")
            return None
        
        # Update progress
        if progress_callback:
            progress_callback(i, total_words, word)
        
        if log_callback:
            log_callback(f"Processing word: {word}")
        
        try:
            # Process the word
            llm_response = generator.generate_content(word)
            processed_result = processor.process_word(word, llm_response)
            
            # Get image if requested
            image_path = None
            if with_images:
                image_path = provider.get_image(word)
                if log_callback and image_path:
                    log_callback(f"Downloaded image for {word}")
            
            # Add the card to the deck
            builder.add_card(processed_result, image_path)
            
            if log_callback:
                log_callback(f"Added card for: {word}")
                
        except Exception as e:
            if log_callback:
                log_callback(f"Error processing word '{word}': {str(e)}")
    
    # Save the deck
    if progress_callback:
        progress_callback(total_words, total_words, "Saving deck...")
    
    builder.save_to_file(output_path)
    
    if log_callback:
        log_callback(f"Saved deck to {output_path}")
    
    # Return the path to the created deck
    return output_path

if __name__ == "__main__":
    main()