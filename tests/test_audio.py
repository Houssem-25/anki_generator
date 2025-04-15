import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Now import the module under test and config
from src import audio_generator
from src import config

# --- Fixtures ---

@pytest.fixture
def temp_audio_file(tmp_path):
    """Creates a dummy audio file in a temporary directory."""
    audio_dir = tmp_path / "audio_src"
    audio_dir.mkdir()
    file_path = audio_dir / "test_audio.mp3"
    file_path.touch() # Create an empty file
    return file_path

@pytest.fixture
def mock_anki_media_dir(tmp_path):
    """Creates a temporary directory to simulate the Anki media directory."""
    anki_dir = tmp_path / "anki_media"
    anki_dir.mkdir()
    return anki_dir

@pytest.fixture(autouse=True)
def setup_config_dirs(tmp_path):
    """Sets up temporary directories in config for testing."""
    original_audio_dir = config.AUDIO_OUTPUT_DIR
    original_anki_dir = config.ANKI_MEDIA_DIR

    # Use temporary directories for testing
    config.AUDIO_OUTPUT_DIR = tmp_path / "test_audio_output"
    config.AUDIO_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    # ANKI_MEDIA_DIR will be set per test using patching or mock_anki_media_dir

    yield # Run the test

    # Restore original config values
    config.AUDIO_OUTPUT_DIR = original_audio_dir
    config.ANKI_MEDIA_DIR = original_anki_dir
    # Clean up temp dirs if necessary (tmp_path fixture handles this)


# --- Tests for copy_to_anki_media ---

@patch('src.config.ANKI_MEDIA_DIR', new_callable=MagicMock)
def test_copy_to_anki_media_success(mock_config_anki_dir, temp_audio_file, mock_anki_media_dir):
    """Test successful copy when ANKI_MEDIA_DIR is set and exists."""
    mock_config_anki_dir.exists.return_value = True
    mock_config_anki_dir.__str__.return_value = str(mock_anki_media_dir) # For print statements
    # Directly assign the Path object for shutil.copy2
    config.ANKI_MEDIA_DIR = mock_anki_media_dir

    result = audio_generator.copy_to_anki_media(temp_audio_file)
    assert result is True
    assert (mock_anki_media_dir / temp_audio_file.name).exists()

@patch('src.config.ANKI_MEDIA_DIR', None)
def test_copy_to_anki_media_not_configured(temp_audio_file, capsys):
    """Test behavior when ANKI_MEDIA_DIR is None."""
    result = audio_generator.copy_to_anki_media(temp_audio_file)
    assert result is False
    captured = capsys.readouterr()
    assert "Warning: Anki media directory not found or not configured" in captured.out

@patch('src.config.ANKI_MEDIA_DIR', new_callable=MagicMock)
def test_copy_to_anki_media_dir_does_not_exist(mock_config_anki_dir, temp_audio_file, capsys):
    """Test behavior when ANKI_MEDIA_DIR is set but doesn't exist."""
    mock_config_anki_dir.exists.return_value = False
    mock_config_anki_dir.__str__.return_value = "/path/does/not/exist"
    config.ANKI_MEDIA_DIR = mock_config_anki_dir # Assign the mock

    result = audio_generator.copy_to_anki_media(temp_audio_file)
    assert result is False
    captured = capsys.readouterr()
    assert "Warning: Anki media directory not found or not configured" in captured.out

@patch('shutil.copy2', side_effect=FileNotFoundError("File not found"))
@patch('src.config.ANKI_MEDIA_DIR', new_callable=MagicMock)
def test_copy_to_anki_media_source_not_found(mock_config_anki_dir, mock_copy, temp_audio_file, mock_anki_media_dir, capsys):
    """Test behavior when the source audio file doesn't exist (mocked)."""
    mock_config_anki_dir.exists.return_value = True
    config.ANKI_MEDIA_DIR = mock_anki_media_dir # Assign the actual path

    result = audio_generator.copy_to_anki_media(temp_audio_file) # temp_audio_file exists, but copy2 raises error
    assert result is False
    captured = capsys.readouterr()
    # Note: The FileNotFoundError will be caught by the specific handler now.
    assert f"Error: Audio file not found at {temp_audio_file}." in captured.out

@patch('shutil.copy2', side_effect=PermissionError("Permission denied"))
@patch('src.config.ANKI_MEDIA_DIR', new_callable=MagicMock)
def test_copy_to_anki_media_permission_error(mock_config_anki_dir, mock_copy, temp_audio_file, mock_anki_media_dir, capsys):
    """Test behavior on permission error during copy (mocked)."""
    mock_config_anki_dir.exists.return_value = True
    config.ANKI_MEDIA_DIR = mock_anki_media_dir

    result = audio_generator.copy_to_anki_media(temp_audio_file)
    assert result is False
    captured = capsys.readouterr()
    assert f"Error: Permission denied copying to {config.ANKI_MEDIA_DIR}." in captured.out


# --- Tests for generate_audio ---

@patch('src.audio_generator.copy_to_anki_media', return_value=True)
@patch('src.audio_generator.gTTS', autospec=True)
def test_generate_audio_success(mock_gtts, mock_copy, tmp_path):
    """Test successful audio generation and copy."""
    test_text = "Hallo Welt"
    expected_filename = "Hallo_Welt.mp3"
    expected_output_file = config.AUDIO_OUTPUT_DIR / expected_filename
    expected_tag = f"[sound:{expected_filename}]"

    # Mock gTTS instance and its save method
    mock_tts_instance = MagicMock()
    mock_gtts.return_value = mock_tts_instance

    result = audio_generator.generate_audio(test_text)

    assert result == expected_tag
    mock_gtts.assert_called_once_with(text=test_text, lang=config.AUDIO_LANG)
    mock_tts_instance.save.assert_called_once_with(expected_output_file)
    mock_copy.assert_called_once_with(expected_output_file)
    # We don't assert file existence because save is mocked

@patch('src.audio_generator.copy_to_anki_media', return_value=True)
@patch('src.audio_generator.gTTS', autospec=True)
def test_generate_audio_sanitizes_filename(mock_gtts, mock_copy):
    """Test filename sanitization."""
    test_text = "Test/Text Mit\\Space"
    expected_filename = "Test_Text_Mit_Space.mp3"
    expected_output_file = config.AUDIO_OUTPUT_DIR / expected_filename
    expected_tag = f"[sound:{expected_filename}]"

    mock_tts_instance = MagicMock()
    mock_gtts.return_value = mock_tts_instance

    result = audio_generator.generate_audio(test_text)

    assert result == expected_tag
    mock_gtts.assert_called_once_with(text=test_text, lang=config.AUDIO_LANG)
    mock_tts_instance.save.assert_called_once_with(expected_output_file)
    mock_copy.assert_called_once_with(expected_output_file)


@patch('src.audio_generator.copy_to_anki_media', return_value=True)
@patch('src.audio_generator.gTTS', autospec=True)
def test_generate_audio_already_exists(mock_gtts, mock_copy):
    """Test behavior when audio file already exists."""
    test_text = "Existing Text"
    expected_filename = "Existing_Text.mp3"
    output_file = config.AUDIO_OUTPUT_DIR / expected_filename
    expected_tag = f"[sound:{expected_filename}]"

    # Create the dummy file
    output_file.touch()

    result = audio_generator.generate_audio(test_text)

    assert result == expected_tag
    mock_gtts.assert_not_called() # Generation should be skipped
    # copy_to_anki_media should still be called
    mock_copy.assert_called_once_with(output_file)


@patch('src.audio_generator.copy_to_anki_media')
@patch('src.audio_generator.gTTS', side_effect=Exception("gTTS Network Error"))
def test_generate_audio_gtts_error(mock_gtts, mock_copy, capsys):
    """Test behavior when gTTS fails."""
    test_text = "Error Text"

    result = audio_generator.generate_audio(test_text)

    assert result == "" # Should return empty string on error
    mock_gtts.assert_called_once_with(text=test_text, lang=config.AUDIO_LANG)
    mock_copy.assert_not_called() # Copy should not happen if generation fails
    captured = capsys.readouterr()
    assert f"Error generating audio for '{test_text}': gTTS Network Error" in captured.out

@patch('src.audio_generator.gTTS')
def test_generate_audio_creates_output_dir(mock_gtts, tmp_path):
    """Test that the output directory is created if it doesn't exist."""
    # Ensure the directory doesn't exist initially for this test
    test_output_dir = tmp_path / "new_audio_output"
    assert not test_output_dir.exists()

    # Patch config *before* calling the function
    with patch('src.config.AUDIO_OUTPUT_DIR', test_output_dir):
        test_text = "Create Dir"
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance
        # We don't care about the return value or copy for this test
        with patch('src.audio_generator.copy_to_anki_media'):
             audio_generator.generate_audio(test_text)

        # Assert that the directory was created
        assert test_output_dir.exists()
        # Assert save was called with the path inside the new dir
        expected_filename = "Create_Dir.mp3"
        expected_output_file = test_output_dir / expected_filename
        mock_tts_instance.save.assert_called_once_with(expected_output_file)
