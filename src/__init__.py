"""
Anki Card Generator - New Architecture

A clean, well-structured Python application for generating Anki flashcards
from German words using AI services.

This package provides:
- Clean architecture with proper separation of concerns
- Modular design with abstract interfaces
- Comprehensive data structures
- Both CLI and GUI interfaces
- Support for multiple AI services
"""

__version__ = "2.0.0"
__author__ = "Anki Generator Team"

from structures import (
    WordData, Card, ProcessingResult, ProcessingOptions,
    ProcessingStats, ProgressUpdate, Configuration,
    WordType, Gender, MediaFile
)

from config import (
    get_config, get_processing_options, validate_config,
    setup_directories, get_api_credentials
)

from processor import create_processor, AnkiCardProcessor

from llm import create_llm_service, LLMService, GroqLLMService

from audio_generator import create_audio_service, AudioService, GTTSAudioService

from image_generator import create_image_service, ImageService, CloudflareImageService

__all__ = [
    # Structures
    'WordData', 'Card', 'ProcessingResult', 'ProcessingOptions',
    'ProcessingStats', 'ProgressUpdate', 'Configuration',
    'WordType', 'Gender', 'MediaFile',
    
    # Configuration
    'get_config', 'get_processing_options', 'validate_config',
    'setup_directories', 'get_api_credentials',
    
    # Processor
    'create_processor', 'AnkiCardProcessor',
    
    # Services
    'create_llm_service', 'LLMService', 'GroqLLMService',
    'create_audio_service', 'AudioService', 'GTTSAudioService',
    'create_image_service', 'ImageService', 'CloudflareImageService',
]
