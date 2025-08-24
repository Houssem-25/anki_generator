"""
Configuration management for the Anki Card Generator.
Handles environment variables, configuration validation, and default settings.
"""

import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

try:
    from structures import Configuration, ProcessingOptions
except ImportError:
    from structures import Configuration, ProcessingOptions


class ConfigManager:
    """Manages application configuration and environment setup."""
    
    def __init__(self):
        self._config: Optional[Configuration] = None
        self._load_environment()
    
    def _load_environment(self):
        """Load environment variables from .env file."""
        # Try to load from current directory first
        env_files = [
            Path(".env"),
            Path("../.env"),
            Path("../../.env"),
        ]
        
        for env_file in env_files:
            if env_file.exists():
                load_dotenv(env_file)
                break
    
    def get_configuration(self) -> Configuration:
        """Get the application configuration."""
        if self._config is None:
            self._config = self._create_configuration()
        return self._config
    
    def _create_configuration(self) -> Configuration:
        """Create configuration from environment variables."""
        return Configuration(
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
            cloudflare_account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID"),
            cloudflare_api_token=os.environ.get("CLOUDFLARE_API_TOKEN"),
            input_file=Path(os.environ.get("INPUT_FILE", "data/input_words.txt")),
            output_file=Path(os.environ.get("OUTPUT_FILE", "anki_output/anki.txt")),
            audio_output_dir=Path(os.environ.get("AUDIO_OUTPUT_DIR", "anki_output/audio")),
            image_output_dir=Path(os.environ.get("IMAGE_OUTPUT_DIR", "anki_output/images")),
            debug_mode=os.environ.get("DEBUG_MODE", "false").lower() == "true"
        )
    
    def validate_configuration(self) -> List[str]:
        """Validate the current configuration."""
        config = self.get_configuration()
        return config.validate()
    
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        config = self.get_configuration()
        
        directories = [
            config.input_file.parent,
            config.output_file.parent,
            config.audio_output_dir,
            config.image_output_dir,
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_processing_options(self, 
                             target_language: str = "english",
                             generate_audio: bool = True,
                             generate_images: bool = True,
                             anki_media_path: Optional[Path] = None,
                             debug_mode: bool = False) -> ProcessingOptions:
        """Create processing options with defaults."""
        config = self.get_configuration()
        
        # Override generate_images if Cloudflare credentials are not available
        if generate_images and not config.generate_images:
            generate_images = False
        
        return ProcessingOptions(
            target_language=target_language,
            generate_audio=generate_audio,
            generate_images=generate_images,
            anki_media_path=anki_media_path,
            debug_mode=debug_mode or config.debug_mode
        )
    
    def update_configuration(self, **kwargs):
        """Update configuration with new values."""
        if self._config is None:
            self._config = self._create_configuration()
        
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    def get_api_credentials(self) -> dict:
        """Get API credentials for external services."""
        config = self.get_configuration()
        
        credentials = {
            "groq_api_key": config.groq_api_key,
        }
        
        if config.cloudflare_account_id and config.cloudflare_api_token:
            credentials.update({
                "cloudflare_account_id": config.cloudflare_account_id,
                "cloudflare_api_token": config.cloudflare_api_token,
            })
        
        return credentials


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> Configuration:
    """Get the application configuration."""
    return config_manager.get_configuration()


def get_processing_options(**kwargs) -> ProcessingOptions:
    """Get processing options with defaults."""
    return config_manager.get_processing_options(**kwargs)


def validate_config() -> List[str]:
    """Validate the current configuration."""
    return config_manager.validate_configuration()


def setup_directories():
    """Setup necessary directories."""
    config_manager.setup_directories()


def get_api_credentials() -> dict:
    """Get API credentials."""
    return config_manager.get_api_credentials()
