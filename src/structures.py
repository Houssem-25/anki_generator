"""
Data structures and entities for the Anki Card Generator.
This module defines all the core data structures used throughout the application.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum


class WordType(Enum):
    """Enumeration for different types of words."""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PREPOSITION = "preposition"
    OTHER = "other"


class Gender(Enum):
    """Enumeration for noun genders."""
    MASCULINE = "masculine"
    FEMININE = "feminine"
    NEUTER = "neuter"


@dataclass
class MediaFile:
    """Represents a media file (audio or image)."""
    filename: str
    file_path: Path
    file_type: str  # 'audio' or 'image'
    content: Optional[bytes] = None
    
    def __post_init__(self):
        if isinstance(self.file_path, str):
            self.file_path = Path(self.file_path)


@dataclass
class WordData:
    """Represents processed data for a single word."""
    word: str
    word_translation: str
    phrase: str
    translation: str
    word_type: WordType
    conjugation: str = ""
    case_info: str = ""
    gender: Optional[Gender] = None
    plural: str = ""
    additional_info: str = ""
    related_words: str = ""
    
    def __post_init__(self):
        if isinstance(self.word_type, str):
            self.word_type = WordType(self.word_type)
        if isinstance(self.gender, str) and self.gender:
            self.gender = Gender(self.gender)


@dataclass
class Card:
    """Represents an Anki card with all its components."""
    front: str  # English side
    back: str   # German side with media
    audio_file: Optional[MediaFile] = None
    image_file: Optional[MediaFile] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_anki_format(self) -> str:
        """Convert card to Anki import format."""
        return f"{self.front};{self.back}"


@dataclass
class ProcessingResult:
    """Result of processing a word."""
    success: bool
    word: str
    card: Optional[Card] = None
    word_data: Optional[WordData] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class ProcessingOptions:
    """Options for word processing."""
    target_language: str = "english"
    generate_audio: bool = True
    generate_images: bool = True
    anki_media_path: Optional[Path] = None
    debug_mode: bool = False
    
    def __post_init__(self):
        if isinstance(self.anki_media_path, str):
            self.anki_media_path = Path(self.anki_media_path)


@dataclass
class ProcessingStats:
    """Statistics for processing session."""
    total_words: int = 0
    processed_words: int = 0
    failed_words: int = 0
    total_time: float = 0.0
    average_time_per_word: float = 0.0
    failed_word_list: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_words == 0:
            return 0.0
        return (self.processed_words / self.total_words) * 100


@dataclass
class Configuration:
    """Application configuration."""
    groq_api_key: str
    cloudflare_account_id: Optional[str] = None
    cloudflare_api_token: Optional[str] = None
    input_file: Path = Path("data/input_words.txt")
    output_file: Path = Path("anki_output/anki.txt")
    audio_output_dir: Path = Path("anki_output/audio")
    image_output_dir: Path = Path("anki_output/images")
    debug_mode: bool = False
    
    def __post_init__(self):
        # Convert string paths to Path objects
        for field_name in ['input_file', 'output_file', 'audio_output_dir', 'image_output_dir']:
            value = getattr(self, field_name)
            if isinstance(value, str):
                setattr(self, field_name, Path(value))
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.groq_api_key:
            errors.append("Groq API key is required")
        
        if self.generate_images and (not self.cloudflare_account_id or not self.cloudflare_api_token):
            errors.append("Cloudflare credentials are required for image generation")
        
        return errors
    
    @property
    def generate_images(self) -> bool:
        """Check if image generation is enabled."""
        return bool(self.cloudflare_account_id and self.cloudflare_api_token)


@dataclass
class ProgressUpdate:
    """Progress update for processing."""
    current: int
    total: int
    current_word: str
    message: str
    progress_percentage: float = 0.0
    
    def __post_init__(self):
        if self.total > 0:
            self.progress_percentage = (self.current / self.total) * 100


# HTML formatting constants
GENDER_TO_ARTICLE_HTML = {
    Gender.MASCULINE: '<span style="color: rgb(10, 2, 255)">Der</span> ',
    Gender.FEMININE: '<span style="color: rgb(170, 0, 0)">Die</span> ',
    Gender.NEUTER: '<span style="color: rgb(0, 255, 51)">Das</span> ',
}

# Default configuration values
DEFAULT_CONFIG = {
    "target_language": "english",
    "generate_audio": True,
    "generate_images": True,
    "debug_mode": False,
}
