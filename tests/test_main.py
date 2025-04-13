import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call, mock_open

# Adjust the path to import from the 'src' directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the main module and config
from src import main
from src import config

# --- Fixtures ---

@pytest.fixture(autouse=True)
def ensure_api_key_unset():
    """Ensure GROQ_API_KEY is not set in the environment before each test, 
       unless specifically set by a test using patch.dict."""
    original_env = os.environ.copy()
    if 'GROQ_API_KEY' in os.environ:
        del os.environ['GROQ_API_KEY']
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture(autouse=True)
def reset_config_media_dir():
    """Resets config.ANKI_MEDIA_DIR after each test."""
    original_dir = config.ANKI_MEDIA_DIR
    yield
    config.ANKI_MEDIA_DIR = original_dir

@pytest.fixture
def mock_dependencies(tmp_path):
    """Mocks the main external dependencies called by main()."""

    # Define paths and content for mocking open
    default_input_path = config.INPUT_WORDS_FILE
    default_content = "test\nword"
    # Path used in test_main_success_custom_args_no_audio
    custom_input_path_for_mock = tmp_path / "my_words.txt"
    custom_content = "custom1\ncustom2"

    # Create the side effect function for builtins.open
    def mock_open_side_effect(file, mode='r', encoding=None):
        file_path = Path(file)
        if file_path == custom_input_path_for_mock:
            # Return the *file handle mock* configured for the custom path
            return mock_open(read_data=custom_content).return_value
        elif file_path == default_input_path:
            # Return the *file handle mock* configured for the default path
            return mock_open(read_data=default_content).return_value
        else:
            # Handle potential unexpected open calls (e.g., during other tests if they call open)
            # print(f"Warning: Mock open called with unexpected path: {file_path}")
            # Return a default empty mock handle
            return mock_open(read_data="").return_value

    # Patch builtins.open using the side_effect
    # mock_open_call will mock the open function itself, side_effect handles the return value (file handle)
    with patch('builtins.open', side_effect=mock_open_side_effect) as mock_open_call, \
         patch('src.main.groq_generator.process_words_file', return_value=(["formatted_line"], [{"word": "test"}])) as mock_process, \
         patch('src.main.anki_generator.write_anki_deck') as mock_write, \
         patch('sys.exit') as mock_exit, \
         patch('pathlib.Path.is_dir', return_value=True) as mock_is_dir:
        # Yield the mocks needed by the tests
        yield mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call # Pass the open mock too

# --- Test Cases ---

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_success_defaults(mock_dependencies, capsys):
    """Test main() runs successfully with default arguments and API key."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    expected_original_words = ["test", "word"] # Based on default_content in side_effect
    
    test_args = ["src/main.py"] # Just the script name
    with patch.object(sys, 'argv', test_args):
        main.main()

    mock_process.assert_called_once_with(input_file_path=config.INPUT_WORDS_FILE)
    mock_write.assert_called_once_with(
        formatted_lines=["formatted_line"],
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True, # Default is True
        original_words=expected_original_words # Check original words are passed
    )
    mock_is_dir.assert_not_called() # Default anki_media_path is None
    mock_exit.assert_not_called()
    captured = capsys.readouterr()
    assert "Anki Card Generation Finished" in captured.out
    assert "Anki media sync directory: Not specified" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_success_custom_args_no_audio(mock_dependencies, tmp_path, capsys):
    """Test main() with custom input/output, no audio, and valid anki media path."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    
    custom_input = tmp_path / "my_words.txt"
    custom_output = tmp_path / "my_anki.txt"
    custom_media = tmp_path / "my_media"
    custom_media.mkdir() # Create the directory
    
    # No longer need to set read_data here, side_effect handles it based on custom_input path
    expected_original_words = ["custom1", "custom2"] # Matches custom_content in side_effect

    test_args = [
        "src/main.py",
        "--input", str(custom_input),
        "--output", str(custom_output),
        "--no-audio",
        "--anki-media-path", str(custom_media)
    ]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mock_process.assert_called_once_with(input_file_path=custom_input)
    mock_write.assert_called_once_with(
        formatted_lines=["formatted_line"],
        output_file_path=custom_output,
        generate_audio_flag=False, # --no-audio flag was set
        original_words=expected_original_words # Check original words are passed
    )
    mock_is_dir.assert_called_once_with() # Called to check the media path
    assert config.ANKI_MEDIA_DIR == custom_media # Check config was updated
    mock_exit.assert_not_called()
    captured = capsys.readouterr()
    assert "Anki Card Generation Finished" in captured.out
    assert f"Anki media sync directory: {custom_media}" in captured.out


def test_main_missing_api_key(mock_dependencies, capsys):
    """Test main() exits if GROQ_API_KEY is not set."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    # Ensure key is NOT in env (handled by fixture)
    
    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mock_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error: Groq API key not found" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_invalid_anki_media_path(mock_dependencies, tmp_path, capsys):
    """Test main() warns and proceeds if --anki-media-path is invalid."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    mock_is_dir.return_value = False # Simulate path is not a directory
    expected_original_words = ["test", "word"] # Based on default_content in side_effect
    
    invalid_media_path = tmp_path / "non_existent_media"
    
    test_args = [
        "src/main.py",
        "--anki-media-path", str(invalid_media_path)
    ]
    with patch.object(sys, 'argv', test_args):
        main.main()

    # Should still proceed with generation
    mock_process.assert_called_once()
    mock_write.assert_called_once_with(
        formatted_lines=["formatted_line"],
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    mock_is_dir.assert_called_once_with() # Checked the path
    assert config.ANKI_MEDIA_DIR is None # Config should remain None
    mock_exit.assert_not_called() # Should not exit due to invalid path
    captured = capsys.readouterr()
    assert f"Warning: Anki media path provided does not exist or is not a directory: {invalid_media_path}" in captured.out
    assert "Audio files will be generated but not copied." in captured.out
    assert "Anki media sync directory: Not specified or path invalid." in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_groq_processing_error(mock_dependencies, capsys):
    """Test main() exits if groq_generator.process_words_file raises error."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    mock_process.side_effect = Exception("Groq API Failed")
    
    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mock_process.assert_called_once()
    mock_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error during Groq API processing: Groq API Failed" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_groq_returns_no_data(mock_dependencies, capsys):
    """Test main() exits if groq_generator.process_words_file returns empty data."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    mock_process.return_value = ([], []) # Simulate no data processed
    
    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mock_process.assert_called_once()
    mock_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error: No data was processed by Groq." in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_anki_generation_error(mock_dependencies, capsys):
    """Test main() exits if anki_generator.write_anki_deck raises error."""
    mock_process, mock_write, mock_exit, mock_is_dir, mock_open_call = mock_dependencies
    mock_write.side_effect = Exception("Anki Write Failed")
    expected_original_words = ["test", "word"]

    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mock_process.assert_called_once()
    mock_write.assert_called_once_with(
        formatted_lines=["formatted_line"],
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    mock_exit.assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error during Anki deck generation: Anki Write Failed" in captured.out
