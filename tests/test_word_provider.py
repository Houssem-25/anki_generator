import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open
from typing import List

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the module under test
from src.word_provider import WordProvider

# --- Fixtures ---

@pytest.fixture
def sample_words() -> List[str]:
    """Returns a list of sample words for testing."""
    return ["Haus", "Auto", "Hund", "Katze"]

@pytest.fixture
def mock_input_file(tmp_path, sample_words):
    """Creates a temporary input file with sample words."""
    input_path = tmp_path / "input_words.txt"
    with open(input_path, 'w', encoding='utf-8') as f:
        for word in sample_words:
            f.write(word + '\n')
    return input_path

@pytest.fixture
def mock_output_file(tmp_path):
    """Creates a temporary output file."""
    return tmp_path / "output.txt"

@pytest.fixture
def word_provider(mock_input_file, mock_output_file):
    """Creates a WordProvider instance with mock files."""
    return WordProvider(mock_input_file, mock_output_file)

# --- Tests for _read_input_words ---

def test_read_input_words_success(mock_input_file, sample_words):
    """Test successful reading of input words."""
    provider = WordProvider(mock_input_file, Path("dummy.txt"))
    words = provider._read_input_words()
    assert words == sample_words

def test_read_input_words_empty_file(tmp_path):
    """Test reading from an empty input file."""
    empty_file = tmp_path / "empty.txt"
    empty_file.touch()
    
    provider = WordProvider(empty_file, Path("dummy.txt"))
    with pytest.raises(SystemExit):
        provider._read_input_words()

def test_read_input_words_file_not_found(tmp_path):
    """Test reading from a non-existent input file."""
    non_existent_file = tmp_path / "nonexistent.txt"
    provider = WordProvider(non_existent_file, Path("dummy.txt"))
    with pytest.raises(SystemExit):
        provider._read_input_words()

# --- Tests for _determine_words_to_process ---

def test_determine_words_to_process_fresh_start(word_provider, sample_words):
    """Test determining words to process with no existing output."""
    words, mode = word_provider._determine_words_to_process(sample_words)
    assert set(words) == set(sample_words)  # Order may be different due to shuffling
    assert mode == 'w'

def test_determine_words_to_process_resume(word_provider, sample_words, mock_output_file):
    """Test determining words to process with existing output."""
    # Create output file with some processed words
    with open(mock_output_file, 'w', encoding='utf-8') as f:
        f.write(f"house;[sound:Haus.mp3]Haus\n")
        f.write(f"car;[sound:Auto.mp3]Auto\n")
    
    words, mode = word_provider._determine_words_to_process(sample_words)
    assert set(words) == {"Hund", "Katze"}  # Only unprocessed words
    assert mode == 'a'

def test_determine_words_to_process_empty_output(word_provider, sample_words, mock_output_file):
    """Test determining words to process with empty output file."""
    mock_output_file.touch()  # Create empty file
    
    words, mode = word_provider._determine_words_to_process(sample_words)
    assert set(words) == set(sample_words)  # All words should be processed
    assert mode == 'w'

def test_determine_words_to_process_invalid_output(word_provider, sample_words, mock_output_file):
    """Test determining words to process with invalid output file."""
    with open(mock_output_file, 'w', encoding='utf-8') as f:
        f.write("invalid line\n")
    
    words, mode = word_provider._determine_words_to_process(sample_words)
    assert set(words) == set(sample_words)  # All words should be processed
    assert mode == 'w'

# --- Tests for _load_and_filter_words ---

def test_load_and_filter_words_success(word_provider, sample_words):
    """Test successful loading and filtering of words."""
    word_provider._load_and_filter_words()
    assert len(word_provider.words_to_process) == len(sample_words)
    assert word_provider.file_mode == 'w'

def test_load_and_filter_words_resume(word_provider, sample_words, mock_output_file):
    """Test loading and filtering with existing output."""
    # Create output file with some processed words
    with open(mock_output_file, 'w', encoding='utf-8') as f:
        f.write(f"house;[sound:Haus.mp3]Haus\n")
        f.write(f"car;[sound:Auto.mp3]Auto\n")
    
    word_provider._load_and_filter_words()
    assert len(word_provider.words_to_process) == 2  # Only unprocessed words
    assert word_provider.file_mode == 'a'

# --- Tests for get_words ---

def test_get_words_iterator(word_provider, sample_words):
    """Test getting words iterator."""
    iterator = word_provider.get_words()
    words = list(iterator)
    assert set(words) == set(sample_words)  # Order may be different due to shuffling

# --- Tests for __len__ ---

def test_len(word_provider, sample_words):
    """Test getting the number of words to process."""
    assert len(word_provider) == len(sample_words)

# --- Tests for get_file_mode ---

def test_get_file_mode(word_provider):
    """Test getting the file mode."""
    assert word_provider.get_file_mode() == 'w'

def test_get_file_mode_resume(word_provider, mock_output_file):
    """Test getting the file mode when resuming."""
    # Create output file with some processed words
    with open(mock_output_file, 'w', encoding='utf-8') as f:
        f.write(f"house;[sound:Haus.mp3]Haus\n")
    
    assert word_provider.get_file_mode() == 'a' 