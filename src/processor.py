"""
Main processor for the Anki Card Generator.
Orchestrates word processing, card generation, and media creation.
"""

import time
from pathlib import Path
from typing import List, Optional, Callable
from dataclasses import dataclass

from structures import (
    WordData, Card, ProcessingResult, ProcessingOptions, 
    ProcessingStats, ProgressUpdate, GENDER_TO_ARTICLE_HTML, MediaFile
)
from llm import create_llm_service
from audio_generator import create_audio_service
from image_generator import create_image_service
from config import get_config, get_api_credentials


@dataclass
class ProcessorConfig:
    """Configuration for the processor."""
    llm_service = None
    audio_service = None
    image_service = None
    config = None
    api_credentials = None


class AnkiCardProcessor:
    """Main processor for generating Anki cards."""
    
    def __init__(self, options: ProcessingOptions):
        self.options = options
        self.config = get_config()
        self.api_credentials = get_api_credentials()
        self.stats = ProcessingStats()
        
        # Initialize services
        self.llm_service = create_llm_service(self.api_credentials["groq_api_key"])
        self.audio_service = create_audio_service()
        
        if self.options.generate_images and "cloudflare_account_id" in self.api_credentials:
            self.image_service = create_image_service(
                self.api_credentials["cloudflare_account_id"],
                self.api_credentials["cloudflare_api_token"]
            )
        else:
            self.image_service = None
    
    def process_words(self, words: List[str], 
                     progress_callback: Optional[Callable[[ProgressUpdate], None]] = None) -> List[ProcessingResult]:
        """Process a list of words and generate Anki cards."""
        self.stats = ProcessingStats(total_words=len(words))
        start_time = time.time()
        
        results = []
        
        for i, word in enumerate(words):
            # Create progress update
            progress = ProgressUpdate(
                current=i,
                total=len(words),
                current_word=word,
                message=f"Processing word: {word}"
            )
            
            if progress_callback:
                progress_callback(progress)
            
            # Process word
            result = self.process_word(word)
            results.append(result)
            
            # Update stats
            if result.success:
                self.stats.processed_words += 1
            else:
                self.stats.failed_words += 1
                self.stats.failed_word_list.append(word)
            
            # Update progress
            progress.current = i + 1
            progress.message = f"Completed: {word}"
            if progress_callback:
                progress_callback(progress)
        
        # Calculate final stats
        self.stats.total_time = time.time() - start_time
        if self.stats.processed_words > 0:
            self.stats.average_time_per_word = self.stats.total_time / self.stats.processed_words
        
        return results
    
    def process_word(self, word: str) -> ProcessingResult:
        """Process a single word and generate an Anki card."""
        start_time = time.time()
        
        try:
            # Step 1: Process word with LLM
            word_data = self.llm_service.process_word(word, self.options.target_language)
            if not word_data:
                return ProcessingResult(
                    success=False,
                    word=word,
                    error_message="Failed to process word with LLM",
                    processing_time=time.time() - start_time
                )
            
            # Step 2: Generate media files
            audio_file = None
            image_file = None
            
            if self.options.generate_audio:
                audio_file = self._generate_audio(word, word_data)
            
            if self.options.generate_images and self.image_service:
                image_file = self._generate_image(word, word_data)
            
            # Step 3: Create Anki card
            card = self._create_card(word_data, audio_file, image_file)
            
            # Step 4: Copy media to Anki directory if specified
            if self.options.anki_media_path:
                self._copy_media_to_anki(audio_file, image_file)
            
            return ProcessingResult(
                success=True,
                word=word,
                card=card,
                word_data=word_data,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return ProcessingResult(
                success=False,
                word=word,
                error_message=str(e),
                processing_time=time.time() - start_time
            )
    
    def _generate_audio(self, word: str, word_data: WordData) -> Optional[MediaFile]:
        """Generate audio for the word."""
        try:
            audio_file = self.audio_service.generate_audio(
                text=word,
                filename=word,
                output_dir=self.config.audio_output_dir
            )
            return audio_file
        except Exception as e:
            print(f"Error generating audio for '{word}': {e}")
            return None
    
    def _generate_image(self, word: str, word_data: WordData) -> Optional[MediaFile]:
        """Generate image for the word."""
        try:
            # Always use English for image prompt to get better quality images
            # Use the stored English translation if available, otherwise fall back to the word
            if word_data.english_translation:
                prompt = word_data.english_translation
            elif word_data.word_translation and all(ord(char) <= 127 for char in word_data.word_translation):
                # If word_translation is in English (only Latin characters), use it
                prompt = word_data.word_translation
            else:
                # Fall back to the German word
                prompt = word
            
            image_file = self.image_service.generate_image(
                prompt=prompt,
                filename=word,
                output_dir=self.config.image_output_dir
            )
            return image_file
        except Exception as e:
            print(f"Error generating image for '{word}': {e}")
            return None
    
    def _create_card(self, word_data: WordData, audio_file: Optional[MediaFile], 
                    image_file: Optional[MediaFile]) -> Card:
        """Create an Anki card from word data and media files."""
        # Create front side (English with image)
        front_parts = []
        
        # Add image if available (at the top of front)
        if image_file:
            front_parts.append(self.image_service.create_image_tag(image_file.filename))
        
        # Add English translation
        front_parts.append(word_data.word_translation)
        if word_data.translation:
            front_parts.append(word_data.translation)
        
        # Join front parts
        front = "<br><br><br>".join(front_parts)
        
        # Create back side (German with audio)
        back_parts = []
        
        # Add German word with grammar info
        german_word = self._format_german_word(word_data)
        back_parts.append(german_word)
        
        # Add example sentence
        if word_data.phrase:
            back_parts.append(word_data.phrase)
        
        # Add related words
        if word_data.related_words:
            back_parts.append(f"Related: {word_data.related_words}")
        
        # Add additional info
        if word_data.additional_info:
            back_parts.append(f"Info: {word_data.additional_info}")
        
        # Add audio if available
        if audio_file:
            back_parts.append(self.audio_service.create_sound_tag(audio_file.filename))
        
        # Join back parts
        back = "<br><br><br>".join(back_parts)
        
        return Card(
            front=front,
            back=back,
            audio_file=audio_file,
            image_file=image_file
        )
    
    def _format_german_word(self, word_data: WordData) -> str:
        """Format German word with grammar information."""
        word = word_data.word
        
        if word_data.word_type.value == "noun" and word_data.gender:
            # Add colored article for nouns
            article_html = GENDER_TO_ARTICLE_HTML.get(word_data.gender, "")
            word_display = f"{article_html}{word}"
            
            # Add plural if available
            if word_data.plural:
                word_display += f" ({word_data.plural})"
            
            return word_display
        
        elif word_data.word_type.value == "verb":
            # Add conjugation info for verbs
            word_display = word
            if word_data.conjugation:
                word_display += f"<br><br><br>Conj: {word_data.conjugation}"
            if word_data.case_info:
                word_display += f"<br><br><br>Case: {word_data.case_info}"
            
            return word_display
        
        else:
            # For other word types, just return the word
            return word
    
    def _copy_media_to_anki(self, audio_file: Optional[MediaFile], image_file: Optional[MediaFile]):
        """Copy media files to Anki media directory."""
        if audio_file:
            self.audio_service.copy_to_anki_media(audio_file, self.options.anki_media_path)
        
        if image_file:
            self.image_service.copy_to_anki_media(image_file, self.options.anki_media_path)
    
    def save_cards_to_file(self, results: List[ProcessingResult], output_file):
        """Save generated cards to Anki import file."""
        try:
            # Convert to Path object if it's a string
            if isinstance(output_file, str):
                output_file = Path(output_file)
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in results:
                    if result.success and result.card:
                        f.write(result.card.to_anki_format() + '\n')
            
            print(f"Cards saved to: {output_file}")
            
        except Exception as e:
            print(f"Error saving cards to file: {e}")
            raise
    
    def get_stats(self) -> ProcessingStats:
        """Get processing statistics."""
        return self.stats
    
    def print_summary(self):
        """Print processing summary."""
        print(f"\n--- Processing Summary ---")
        print(f"Total words: {self.stats.total_words}")
        print(f"Successfully processed: {self.stats.processed_words}")
        print(f"Failed: {self.stats.failed_words}")
        print(f"Success rate: {self.stats.success_rate:.1f}%")
        print(f"Total time: {self.stats.total_time:.2f}s")
        print(f"Average time per word: {self.stats.average_time_per_word:.2f}s")
        
        if self.stats.failed_word_list:
            print(f"Failed words: {', '.join(self.stats.failed_word_list)}")


def create_processor(options: ProcessingOptions) -> AnkiCardProcessor:
    """Factory function to create processor."""
    return AnkiCardProcessor(options)
