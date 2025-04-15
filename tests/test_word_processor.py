import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import Dict, Any

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the module under test
from src.word_processor import WordProcessor

# --- Fixtures ---

@pytest.fixture
def mock_args():
    """Creates a mock args object with default values."""
    args = MagicMock()
    args.no_audio = False
    return args

@pytest.fixture
def sample_word_data() -> Dict[str, Any]:
    """Returns sample word data for testing."""
    return {
        "word": "Haus",
        "word_translation": "house",
        "phrase": "Das ist mein Haus.",
        "translation": "This is my house.",
        "word_type": "noun",
        "gender": "neuter",
        "plural": "Häuser",
        "related_words": "Gebäude, Wohnung",
        "additional_info": "Common noun"
    }

@pytest.fixture
def word_processor(mock_args):
    """Creates a WordProcessor instance with mocked args."""
    return WordProcessor(mock_args, can_generate_images=True)

# --- Tests for _sanitize_filename ---

def test_sanitize_filename_basic(word_processor):
    """Test basic filename sanitization."""
    assert word_processor._sanitize_filename("Haus") == "Haus"
    assert word_processor._sanitize_filename("Haus mit Garten") == "Haus_mit_Garten"
    assert word_processor._sanitize_filename("Haus/Garten") == "Haus_Garten"

def test_sanitize_filename_special_chars(word_processor):
    """Test sanitization of special characters."""
    assert word_processor._sanitize_filename("Haus!@#$%^&*()") == "Haus"
    assert word_processor._sanitize_filename("Haus mit Umlauten äöü") == "Haus_mit_Umlauten_äöü"

def test_sanitize_filename_empty(word_processor):
    """Test sanitization of empty or invalid filenames."""
    assert word_processor._sanitize_filename("") == "unnamed"
    assert word_processor._sanitize_filename("!@#$%") == "unnamed"

# --- Tests for process_word ---

@patch('src.word_processor.WordProcessor._generate_text')
@patch('src.word_processor.WordProcessor._format_base_line')
@patch('src.word_processor.WordProcessor._generate_image')
@patch('src.word_processor.WordProcessor._generate_audio')
def test_process_word_success(mock_generate_audio, mock_generate_image, mock_format_base_line, 
                            mock_generate_text, word_processor, sample_word_data):
    """Test successful word processing with all components."""
    # Setup mocks
    mock_generate_text.return_value = sample_word_data
    mock_format_base_line.return_value = "house;Haus"
    mock_generate_image.return_value = "<img src='Haus.png'>"
    mock_generate_audio.return_value = "[sound:Haus.mp3]"
    
    result = word_processor.process_word("Haus")
    
    assert result == "<img src='Haus.png'>house;[sound:Haus.mp3]Haus"
    mock_generate_text.assert_called_once_with("Haus")
    mock_format_base_line.assert_called_once_with(sample_word_data)
    mock_generate_image.assert_called_once_with("Haus", sample_word_data)
    mock_generate_audio.assert_called_once_with("Haus")

@patch('src.word_processor.WordProcessor._generate_text')
def test_process_word_text_generation_failure(mock_generate_text, word_processor):
    """Test word processing when text generation fails."""
    mock_generate_text.return_value = None
    
    result = word_processor.process_word("Haus")
    
    assert result is None
    mock_generate_text.assert_called_once_with("Haus")

@patch('src.word_processor.WordProcessor._generate_text')
@patch('src.word_processor.WordProcessor._format_base_line')
def test_process_word_format_failure(mock_format_base_line, mock_generate_text, word_processor, sample_word_data):
    """Test word processing when formatting fails."""
    mock_generate_text.return_value = sample_word_data
    mock_format_base_line.return_value = None
    
    result = word_processor.process_word("Haus")
    
    assert result is None
    mock_generate_text.assert_called_once_with("Haus")
    mock_format_base_line.assert_called_once_with(sample_word_data)

# --- Tests for _parse_retry_after ---

def test_parse_retry_after_seconds(word_processor):
    """Test parsing retry time in seconds."""
    error_msg = "Rate limit exceeded. Please try again in 30s."
    assert word_processor._parse_retry_after(error_msg) == 31.0  # 30s + 1s buffer

def test_parse_retry_after_minutes_seconds(word_processor):
    """Test parsing retry time with minutes and seconds."""
    error_msg = "Rate limit exceeded. Please try again in 1m30s."
    assert word_processor._parse_retry_after(error_msg) == 91.0  # 60s + 30s + 1s buffer

def test_parse_retry_after_invalid_format(word_processor):
    """Test parsing retry time with invalid format."""
    error_msg = "Invalid error message format"
    assert word_processor._parse_retry_after(error_msg) == 60.0  # Default value

# --- Tests for _handle_groq_error ---

def test_handle_groq_error_rate_limit(word_processor):
    """Test handling rate limit error."""
    error = MagicMock()
    error.__class__.__name__ = "RateLimitError"
    error.detail = "Rate limit exceeded. Please try again in 30s."
    
    should_retry, delay, retries = word_processor._handle_groq_error(error, "Haus", 0)
    
    assert should_retry is True
    assert delay == 31.0
    assert retries == 1

def test_handle_groq_error_api_error(word_processor):
    """Test handling API error."""
    error = MagicMock()
    error.__class__.__name__ = "APIError"
    
    should_retry, delay, retries = word_processor._handle_groq_error(error, "Haus", 0)
    
    assert should_retry is True
    assert delay == 15.0
    assert retries == 0

def test_handle_groq_error_max_retries(word_processor):
    """Test handling error when max retries reached."""
    error = MagicMock()
    error.__class__.__name__ = "RateLimitError"
    error.detail = "Rate limit exceeded. Please try again in 30s."
    
    should_retry, delay, retries = word_processor._handle_groq_error(error, "Haus", 49)  # MAX_GROQ_RETRIES = 50
    
    assert should_retry is False
    assert delay == 0
    assert retries == 50

# --- Tests for _generate_text ---

@patch('src.llm_generator.process_german_words')
def test_generate_text_success(mock_process_words, word_processor, sample_word_data):
    """Test successful text generation."""
    mock_process_words.return_value = [sample_word_data]
    
    result = word_processor._generate_text("Haus")
    
    assert result == sample_word_data
    mock_process_words.assert_called_once_with(["Haus"])

@patch('src.llm_generator.process_german_words')
def test_generate_text_empty_result(mock_process_words, word_processor):
    """Test text generation with empty result."""
    mock_process_words.return_value = []
    
    result = word_processor._generate_text("Haus")
    
    assert result is None
    mock_process_words.assert_called_once_with(["Haus"])

# --- Tests for _format_base_line ---

@patch('src.llm_generator.format_for_anki_import')
def test_format_base_line_success(mock_format, word_processor, sample_word_data):
    """Test successful base line formatting."""
    mock_format.return_value = ["house;Haus"]
    
    result = word_processor._format_base_line(sample_word_data)
    
    assert result == "house;Haus"
    mock_format.assert_called_once_with([sample_word_data])

@patch('src.llm_generator.format_for_anki_import')
def test_format_base_line_empty_result(mock_format, word_processor, sample_word_data):
    """Test base line formatting with empty result."""
    mock_format.return_value = []
    
    result = word_processor._format_base_line(sample_word_data)
    
    assert result is None
    mock_format.assert_called_once_with([sample_word_data])

# --- Tests for _generate_image ---

@patch('src.image_generator.generate_image_for_prompt')
def test_generate_image_success(mock_generate_image, word_processor, sample_word_data):
    """Test successful image generation."""
    mock_generate_image.return_value = "base64_image_data"
    
    result = word_processor._generate_image("Haus", sample_word_data)
    
    assert result == "<img src='Haus.png'>"
    mock_generate_image.assert_called_once_with(
        word_translation=sample_word_data["word_translation"],
        english_sentence=sample_word_data["translation"],
        account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID"),
        api_token=os.environ.get("CLOUDFLARE_API_TOKEN")
    )

@patch('src.image_generator.generate_image_for_prompt')
def test_generate_image_failure(mock_generate_image, word_processor, sample_word_data):
    """Test image generation failure."""
    mock_generate_image.return_value = None
    
    result = word_processor._generate_image("Haus", sample_word_data)
    
    assert result == ""
    mock_generate_image.assert_called_once()

# --- Tests for _generate_audio ---

@patch('src.audio_generator.generate_audio')
def test_generate_audio_success(mock_generate_audio, word_processor):
    """Test successful audio generation."""
    mock_generate_audio.return_value = "[sound:Haus.mp3]"
    
    result = word_processor._generate_audio("Haus")
    
    assert result == "[sound:Haus.mp3]"
    mock_generate_audio.assert_called_once_with("Haus", "Haus")

def test_generate_audio_disabled(word_processor):
    """Test audio generation when disabled."""
    word_processor.args.no_audio = True
    
    result = word_processor._generate_audio("Haus")
    
    assert result == "" 