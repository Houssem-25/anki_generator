"""
Audio generation service using Google Text-to-Speech (gTTS).
Handles audio file generation and management.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod
from gtts import gTTS

from structures import MediaFile


class AudioService(ABC):
    """Abstract base class for audio services."""
    
    @abstractmethod
    def generate_audio(self, text: str, filename: str, output_dir: Path) -> Optional[MediaFile]:
        """Generate audio file from text."""
        pass
    
    @abstractmethod
    def copy_to_anki_media(self, media_file: MediaFile, anki_media_path: Path) -> bool:
        """Copy audio file to Anki media directory."""
        pass


class GTTSAudioService(AudioService):
    """Google TTS implementation for audio generation."""
    
    def __init__(self, language: str = 'de'):
        self.language = language
    
    def generate_audio(self, text: str, filename: str, output_dir: Path) -> Optional[MediaFile]:
        """Generate audio file from text using gTTS."""
        if not text or not filename:
            print("Warning: generate_audio called with empty text or filename.")
            return None
        
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create full file path
            safe_filename = self._sanitize_filename(filename)
            audio_filename = f"{safe_filename}.mp3"
            output_path = output_dir / audio_filename
            
            # Check if file already exists
            if output_path.exists():
                print(f"Audio file already exists: {output_path}")
                return MediaFile(
                    filename=audio_filename,
                    file_path=output_path,
                    file_type="audio"
                )
            
            # Generate audio using gTTS
            tts = gTTS(text=text, lang=self.language)
            tts.save(str(output_path))
            
            print(f"Audio saved to: {output_path}")
            
            return MediaFile(
                filename=audio_filename,
                file_path=output_path,
                file_type="audio"
            )
            
        except Exception as e:
            print(f"Error generating audio for '{text}': {e}")
            return None
    
    def copy_to_anki_media(self, media_file: MediaFile, anki_media_path: Path) -> bool:
        """Copy audio file to Anki media directory."""
        if not anki_media_path or not anki_media_path.is_dir():
            print(f"Warning: Anki media directory not found or not a directory: {anki_media_path}")
            return False
        
        try:
            # Ensure Anki media directory exists
            anki_media_path.mkdir(parents=True, exist_ok=True)
            
            # Create destination path
            dest_path = anki_media_path / media_file.filename
            
            # Copy file
            shutil.copy2(media_file.file_path, dest_path)
            print(f"Audio file copied to Anki media: {dest_path}")
            
            return True
            
        except Exception as e:
            print(f"Warning: Failed to copy audio '{media_file.filename}' to Anki media: {e}")
            return False
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use as a filename."""
        # Replace spaces and special characters with underscores
        # Keep umlauts and other German characters
        sanitized = text.strip()
        sanitized = ''.join(c if c.isalnum() or c in 'äöüÄÖÜß' else '_' for c in sanitized)
        return sanitized
    
    def create_sound_tag(self, filename: str) -> str:
        """Create Anki sound tag for the audio file."""
        return f"[sound:{filename}]"


class MockAudioService(AudioService):
    """Mock audio service for testing."""
    
    def __init__(self):
        self.generated_files = []
        self.copied_files = []
    
    def generate_audio(self, text: str, filename: str, output_dir: Path) -> Optional[MediaFile]:
        """Mock audio generation."""
        safe_filename = self._sanitize_filename(filename)
        audio_filename = f"{safe_filename}.mp3"
        output_path = output_dir / audio_filename
        
        # Create empty file for testing
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.touch()
        
        media_file = MediaFile(
            filename=audio_filename,
            file_path=output_path,
            file_type="audio"
        )
        
        self.generated_files.append(media_file)
        return media_file
    
    def copy_to_anki_media(self, media_file: MediaFile, anki_media_path: Path) -> bool:
        """Mock copy to Anki media."""
        self.copied_files.append((media_file, anki_media_path))
        return True
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use as a filename."""
        sanitized = text.strip()
        sanitized = ''.join(c if c.isalnum() or c in 'äöüÄÖÜß' else '_' for c in sanitized)
        return sanitized
    
    def create_sound_tag(self, filename: str) -> str:
        """Create Anki sound tag for the audio file."""
        return f"[sound:{filename}]"


def create_audio_service(language: str = 'de') -> AudioService:
    """Factory function to create audio service."""
    return GTTSAudioService(language)


def create_mock_audio_service() -> AudioService:
    """Factory function to create mock audio service for testing."""
    return MockAudioService()
