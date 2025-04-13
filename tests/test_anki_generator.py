import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open, call, MagicMock

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Now import the module under test
from src import anki_generator
from src import config # Needed for gender constants

# --- Fixtures ---

@pytest.fixture
def mock_output_dir(tmp_path):
    """Creates a temporary directory for output files."""
    out_dir = tmp_path / "test_output"
    # The function itself calls os.makedirs, so we don't need to create it here
    # out_dir.mkdir()
    return out_dir

@pytest.fixture
def sample_original_words():
    return ["Hallo", "Welt", "Katze", "Eine komplizierte Phrase"]

@pytest.fixture
def sample_formatted_lines_simple():
    return [
        "hello;Hallo",
        "world;<span style=\"color: rgb(170, 0, 0)\">Die</span> Welt",
        "cat;<span style=\"color: rgb(170, 0, 0)\">Die</span> Katze (-n)",
        "complex phrase;Eine komplizierte<br>Phrase",
    ]

# --- Tests for write_anki_deck ---

@patch('src.anki_generator.audio.generate_audio')
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_write_anki_deck_success_with_audio(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir, sample_formatted_lines_simple, sample_original_words):
    """Test successful deck writing with audio generation enabled."""
    output_file = mock_output_dir / "anki_test.txt"
    formatted_lines = sample_formatted_lines_simple
    original_words = sample_original_words

    # Expected audio calls should now use the original words
    expected_audio_calls = [call(w) for w in original_words]
    mock_generate_audio.side_effect = [
        "[sound:Hallo.mp3]",
        "[sound:Welt.mp3]",
        "[sound:Katze.mp3]",
        "[sound:Eine_komplizierte.mp3]",
    ]

    expected_output_lines = [
        "hello;[sound:Hallo.mp3]Hallo\n",
        "world;[sound:Welt.mp3]<span style=\"color: rgb(170, 0, 0)\">Die</span> Welt\n",
        "cat;[sound:Katze.mp3]<span style=\"color: rgb(170, 0, 0)\">Die</span> Katze (-n)\n",
        "complex phrase;[sound:Eine_komplizierte.mp3]Eine komplizierte<br>Phrase\n",
    ]

    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=True, original_words=original_words)

    mock_makedirs.assert_called_once_with(mock_output_dir, exist_ok=True)
    mock_generate_audio.assert_has_calls(expected_audio_calls, any_order=False)
    assert mock_generate_audio.call_count == len(expected_audio_calls)
    mock_file_open.assert_called_once_with(output_file, 'w', encoding='utf-8')
    handle = mock_file_open()
    handle.write.assert_has_calls([call(line) for line in expected_output_lines])

@patch('src.anki_generator.audio.generate_audio')
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_write_anki_deck_success_without_audio(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir):
    """Test successful deck writing with audio generation disabled."""
    output_file = mock_output_dir / "anki_test_no_audio.txt"
    formatted_lines = [
        "hello;Hallo",
        "world;Die Welt",
    ]
    original_words = ["Hallo", "Welt"] # Provide dummy original words
    expected_output_lines = [
        "hello;Hallo\n",
        "world;Die Welt\n",
    ]

    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=False, original_words=original_words)

    mock_makedirs.assert_called_once_with(mock_output_dir, exist_ok=True)
    mock_generate_audio.assert_not_called()
    mock_file_open.assert_called_once_with(output_file, 'w', encoding='utf-8')
    handle = mock_file_open()
    handle.write.assert_has_calls([call(line) for line in expected_output_lines])

@patch('src.anki_generator.audio.generate_audio')
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_write_anki_deck_skips_invalid_lines(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir, capsys):
    """Test that lines with incorrect format are skipped."""
    output_file = mock_output_dir / "anki_test_invalid.txt"
    formatted_lines = [
        "hello;Hallo",
        "invalidline", # Missing semicolon
        "world;Die Welt",
        "another;Valid;Line", # Extra semicolon, handled by split(';', 1)
    ]
    # Original words list needs to match formatted_lines length initially
    original_words = ["Hallo", "invalid", "Welt", "Valid"] 
    # Audio should only be generated for valid lines based on original_words
    expected_audio_calls = [
        call("Hallo"), 
        call("Welt"), 
        call("Valid")
    ]
    mock_generate_audio.side_effect = [
        "[sound:Hallo.mp3]",
        "[sound:Welt.mp3]",
        "[sound:Valid.mp3]",
    ]

    expected_output_lines = [
        "hello;[sound:Hallo.mp3]Hallo\n",
        "world;[sound:Welt.mp3]Die Welt\n",
        "another;[sound:Valid.mp3]Valid;Line\n",
    ]

    # Note: The function might now raise an error or return early if lengths mismatch
    # depending on implementation. Assuming it continues after printing errors.
    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=True, original_words=original_words)

    mock_makedirs.assert_called_once_with(mock_output_dir, exist_ok=True)
    assert mock_generate_audio.call_count == 3
    mock_file_open.assert_called_once_with(output_file, 'w', encoding='utf-8')
    handle = mock_file_open()
    handle.write.assert_has_calls([call(line) for line in expected_output_lines])

    captured = capsys.readouterr()
    assert "Warning: Skipping line due to unexpected format: invalidline" in captured.out

@patch('src.anki_generator.audio.generate_audio', return_value="")
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_write_anki_deck_handles_empty_audio_tag(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir):
    """Test that an empty audio tag is handled correctly (e.g., audio gen failure)."""
    output_file = mock_output_dir / "anki_test_empty_audio.txt"
    formatted_lines = ["hello;Hallo"]
    original_words = ["Hallo"]
    expected_output_lines = ["hello;Hallo\n"] # No sound tag prepended

    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=True, original_words=original_words)

    mock_makedirs.assert_called_once_with(mock_output_dir, exist_ok=True)
    mock_generate_audio.assert_called_once_with("Hallo")
    mock_file_open.assert_called_once_with(output_file, 'w', encoding='utf-8')
    handle = mock_file_open()
    handle.write.assert_has_calls([call(line) for line in expected_output_lines])

@patch('src.anki_generator.audio.generate_audio')
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_write_anki_deck_no_lines_processed(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir, capsys):
    """Test behavior when no valid lines are processed."""
    output_file = mock_output_dir / "anki_test_no_lines.txt"
    formatted_lines = ["invalid1", "invalid2"] # Only invalid lines
    original_words = ["invalid1", "invalid2"] # Matching original words

    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=True, original_words=original_words)

    mock_makedirs.assert_called_once_with(mock_output_dir, exist_ok=True)
    mock_generate_audio.assert_not_called()
    mock_file_open.assert_not_called() # File should not be opened/written

    captured = capsys.readouterr()
    assert "Warning: Skipping line" in captured.out # Warnings for invalid lines
    assert "Error: No valid lines were processed" in captured.out # Final error message

@patch('src.anki_generator.audio.generate_audio')
@patch('os.makedirs')
@patch('builtins.open', side_effect=IOError("Disk full"))
def test_write_anki_deck_file_write_error(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir, capsys):
    """Test handling of exceptions during file writing."""
    output_file = mock_output_dir / "anki_test_write_error.txt"
    formatted_lines = ["hello;Hallo"]
    original_words = ["Hallo"]
    mock_generate_audio.return_value = "[sound:Hallo.mp3]"

    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=True, original_words=original_words)

    mock_makedirs.assert_called_once_with(mock_output_dir, exist_ok=True)
    mock_generate_audio.assert_called_once_with("Hallo")
    mock_file_open.assert_called_once_with(output_file, 'w', encoding='utf-8')

    captured = capsys.readouterr()
    assert f"Error saving Anki deck to {output_file}: Disk full" in captured.out

@patch('src.anki_generator.audio.generate_audio')
@patch('os.makedirs')
@patch('builtins.open', new_callable=mock_open)
def test_write_anki_deck_cleans_term_for_audio(mock_file_open, mock_makedirs, mock_generate_audio, mock_output_dir):
    """Test that original words are used directly for audio generation."""
    output_file = mock_output_dir / "anki_test_clean.txt"
    formatted_lines = [
        f"the man;{config.GENDER_TO_ARTICLE_HTML['m']}Mann",
        f"the woman;{config.GENDER_TO_ARTICLE_HTML['f']} Frau (en)",
        f"the child;{config.GENDER_TO_ARTICLE_HTML['n']}Kind (-er)<br>Some example",
        f"the people;{config.GENDER_TO_ARTICLE_HTML['p']}Leute"
    ]
    # Original words that should be used for audio
    original_words = ["Mann", "Frau", "Kind", "Leute"]
    expected_audio_calls = [call(w) for w in original_words] # Calls should use original words

    mock_generate_audio.return_value = "[sound:dummy.mp3]" # Return value doesn't matter here

    anki_generator.write_anki_deck(formatted_lines, output_file, generate_audio_flag=True, original_words=original_words)

    # Assert that generate_audio was called with the original words
    mock_generate_audio.assert_has_calls(expected_audio_calls, any_order=False)
    assert mock_generate_audio.call_count == len(expected_audio_calls)
