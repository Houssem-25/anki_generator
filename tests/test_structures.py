"""
Tests for data structures and entities.
"""

import pytest
from pathlib import Path

from ..structures import (
    WordData, Card, ProcessingResult, ProcessingOptions,
    ProcessingStats, ProgressUpdate, Configuration,
    WordType, Gender, MediaFile
)


class TestWordData:
    """Test WordData entity."""
    
    def test_word_data_creation(self):
        """Test creating WordData instance."""
        word_data = WordData(
            word="Haus",
            word_translation="house",
            phrase="Das Haus ist groß.",
            translation="The house is big.",
            word_type=WordType.NOUN,
            gender=Gender.NEUTER,
            plural="Häuser"
        )
        
        assert word_data.word == "Haus"
        assert word_data.word_translation == "house"
        assert word_data.word_type == WordType.NOUN
        assert word_data.gender == Gender.NEUTER
        assert word_data.plural == "Häuser"
    
    def test_word_data_string_conversion(self):
        """Test string to enum conversion."""
        word_data = WordData(
            word="gehen",
            word_translation="to go",
            phrase="Ich gehe nach Hause.",
            translation="I go home.",
            word_type="verb",  # String should be converted to enum
            gender="masculine"  # String should be converted to enum
        )
        
        assert word_data.word_type == WordType.VERB
        assert word_data.gender == Gender.MASCULINE


class TestCard:
    """Test Card entity."""
    
    def test_card_creation(self):
        """Test creating Card instance."""
        card = Card(
            front="house",
            back="<img src='Haus.png'><br>Das Haus<br>Audio: [sound:Haus.mp3]"
        )
        
        assert card.front == "house"
        assert "Das Haus" in card.back
        assert card.to_anki_format() == "house;<img src='Haus.png'><br>Das Haus<br>Audio: [sound:Haus.mp3]"


class TestProcessingResult:
    """Test ProcessingResult entity."""
    
    def test_successful_result(self):
        """Test successful processing result."""
        result = ProcessingResult(
            success=True,
            word="Haus",
            processing_time=1.5
        )
        
        assert result.success is True
        assert result.word == "Haus"
        assert result.processing_time == 1.5
        assert result.error_message is None
    
    def test_failed_result(self):
        """Test failed processing result."""
        result = ProcessingResult(
            success=False,
            word="InvalidWord",
            error_message="API error occurred",
            processing_time=0.5
        )
        
        assert result.success is False
        assert result.error_message == "API error occurred"


class TestProcessingOptions:
    """Test ProcessingOptions entity."""
    
    def test_default_options(self):
        """Test default processing options."""
        options = ProcessingOptions()
        
        assert options.target_language == "english"
        assert options.generate_audio is True
        assert options.generate_images is True
        assert options.debug_mode is False
    
    def test_custom_options(self):
        """Test custom processing options."""
        options = ProcessingOptions(
            target_language="french",
            generate_audio=False,
            generate_images=False,
            debug_mode=True
        )
        
        assert options.target_language == "french"
        assert options.generate_audio is False
        assert options.generate_images is False
        assert options.debug_mode is True


class TestProcessingStats:
    """Test ProcessingStats entity."""
    
    def test_stats_creation(self):
        """Test creating ProcessingStats instance."""
        stats = ProcessingStats(
            total_words=10,
            processed_words=8,
            failed_words=2,
            total_time=15.5
        )
        
        assert stats.total_words == 10
        assert stats.processed_words == 8
        assert stats.failed_words == 2
        assert stats.total_time == 15.5
        assert stats.success_rate == 80.0
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        stats = ProcessingStats(total_words=0)
        assert stats.success_rate == 0.0
        
        stats = ProcessingStats(total_words=5, processed_words=5)
        assert stats.success_rate == 100.0
        
        stats = ProcessingStats(total_words=10, processed_words=7)
        assert stats.success_rate == 70.0


class TestProgressUpdate:
    """Test ProgressUpdate entity."""
    
    def test_progress_creation(self):
        """Test creating ProgressUpdate instance."""
        progress = ProgressUpdate(
            current=5,
            total=10,
            current_word="Haus",
            message="Processing word: Haus"
        )
        
        assert progress.current == 5
        assert progress.total == 10
        assert progress.current_word == "Haus"
        assert progress.progress_percentage == 50.0
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        progress = ProgressUpdate(current=0, total=0, current_word="", message="")
        assert progress.progress_percentage == 0.0
        
        progress = ProgressUpdate(current=5, total=10, current_word="", message="")
        assert progress.progress_percentage == 50.0
        
        progress = ProgressUpdate(current=10, total=10, current_word="", message="")
        assert progress.progress_percentage == 100.0


class TestConfiguration:
    """Test Configuration entity."""
    
    def test_configuration_creation(self):
        """Test creating Configuration instance."""
        config = Configuration(
            groq_api_key="test_key",
            cloudflare_account_id="test_account",
            cloudflare_api_token="test_token"
        )
        
        assert config.groq_api_key == "test_key"
        assert config.cloudflare_account_id == "test_account"
        assert config.cloudflare_api_token == "test_token"
        assert config.generate_images is True
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config = Configuration(groq_api_key="test_key")
        errors = config.validate()
        assert len(errors) == 0
        
        # Invalid configuration - missing API key
        config = Configuration(groq_api_key="")
        errors = config.validate()
        assert len(errors) == 1
        assert "Groq API key is required" in errors[0]
    
    def test_path_conversion(self):
        """Test string to Path conversion."""
        config = Configuration(
            groq_api_key="test_key",
            input_file="data/input.txt",
            output_file="output/result.txt"
        )
        
        assert isinstance(config.input_file, Path)
        assert isinstance(config.output_file, Path)
        assert str(config.input_file) == "data/input.txt"
        assert str(config.output_file) == "output/result.txt"


class TestMediaFile:
    """Test MediaFile entity."""
    
    def test_media_file_creation(self):
        """Test creating MediaFile instance."""
        media_file = MediaFile(
            filename="test.mp3",
            file_path="audio/test.mp3",
            file_type="audio"
        )
        
        assert media_file.filename == "test.mp3"
        assert isinstance(media_file.file_path, Path)
        assert media_file.file_type == "audio"
    
    def test_string_path_conversion(self):
        """Test string to Path conversion."""
        media_file = MediaFile(
            filename="test.png",
            file_path="images/test.png",
            file_type="image"
        )
        
        assert isinstance(media_file.file_path, Path)
        assert str(media_file.file_path) == "images/test.png"
