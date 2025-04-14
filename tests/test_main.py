import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, call, mock_open, ANY
import base64
import shutil

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
    # Store the original os.environ.get before patching
    original_os_environ_get = os.environ.get

    # Define paths and content for mocking open
    default_input_path = config.INPUT_WORDS_FILE
    # More realistic Groq output structure
    mock_groq_processed_data = [
        {"word": "Wort1", "word_translation": "Word1", "translation": "Sentence 1.", "gender": "n", "plural": "Wörter1", "genitive": "Wortes1", "german_sentence": "Satz 1."},
        {"word": "Wort2", "word_translation": "Word2", "translation": "Sentence 2.", "gender": "f", "plural": "Wörter2", "genitive": "Wortes2", "german_sentence": "Satz 2."}
    ]
    mock_groq_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mock_groq_processed_data]
    default_content = "\n".join([d['word'] for d in mock_groq_processed_data])
    # Path used in test_main_success_custom_args_no_audio
    custom_input_path_for_mock = tmp_path / "my_words.txt"
    custom_content = "custom1\ncustom2"

    # Create the side effect function for builtins.open
    def mock_open_side_effect(file, mode='r', encoding=None):
        file_path = Path(file)
        # Handle reading input files
        if mode == 'r' or mode == 'rt':
            if file_path == custom_input_path_for_mock:
                print(f"Mocking open({file_path}, '{mode}') for custom input")
                return mock_open(read_data=custom_content).return_value
            elif file_path == default_input_path:
                print(f"Mocking open({file_path}, '{mode}') for default input")
                return mock_open(read_data=default_content).return_value
            else:
                # Fallback for other reads if necessary, though ideally specific paths are matched
                print(f"Warning: Mock open({file_path}, '{mode}') called unexpectedly - returning empty mock")
                return mock_open(read_data="").return_value
        # Handle writing image files
        elif mode == 'wb':
            # Check if the path seems like an image file in the expected output dir
            # This check might need adjustment based on actual image filenames used
            if config.IMAGE_OUTPUT_DIR in file_path.parents:
                 print(f"Mocking open({file_path}, '{mode}') for image write")
                 # Return a MagicMock that simulates a file handle for writing binary
                 mock_file_handle = MagicMock()
                 mock_file_handle.__enter__.return_value.write = MagicMock()
                 return mock_file_handle
            else:
                 print(f"Warning: Mock open({file_path}, '{mode}') called unexpectedly - returning default mock")
                 # Fallback for unexpected binary writes
                 return mock_open().return_value # Basic mock_open handle
        # Handle other modes if necessary
        else:
            print(f"Warning: Mock open({file_path}, '{mode}') called with unhandled mode - returning default mock")
            return mock_open().return_value

    # Patch builtins.open using the side_effect
    # mock_open_call will mock the open function itself, side_effect handles the return value (file handle)
    with patch('builtins.open', side_effect=mock_open_side_effect) as mock_open_call, \
         patch('src.main.groq_generator.process_words_file', return_value=(mock_groq_formatted_lines, mock_groq_processed_data)) as mock_process, \
         patch('src.main.anki_generator.write_anki_deck') as mock_write, \
         patch('sys.exit') as mock_exit, \
         patch('pathlib.Path.is_dir', return_value=True) as mock_is_dir, \
         patch('pathlib.Path.mkdir') as mock_mkdir, \
         patch('os.environ.get') as mock_env_get, \
         patch('src.main.generate_image_for_prompt', return_value=base64.b64encode(b"fakedata").decode('ascii')) as mock_gen_image, \
         patch('base64.b64decode', return_value=b"fakedata") as mock_b64decode, \
         patch('shutil.copy2') as mock_copy2:

        # Default mock for environment variables (can be overridden by tests)
        def env_get_side_effect(key, default=None):
            if key == 'CLOUDFLARE_ACCOUNT_ID': return 'fake_acc_id' # Handled by mock
            if key == 'CLOUDFLARE_API_TOKEN': return 'fake_api_token' # Handled by mock
            return original_os_environ_get(key, default) # Use original for others
        mock_env_get.side_effect = env_get_side_effect

        # Yield the mocks needed by the tests
        yield {
            "process": mock_process, "write": mock_write, "exit": mock_exit,
            "is_dir": mock_is_dir, "open": mock_open_call, "mkdir": mock_mkdir,
            "env_get": mock_env_get, "gen_image": mock_gen_image,
            "b64decode": mock_b64decode, "copy2": mock_copy2,
            "groq_data": mock_groq_processed_data, # Pass sample data too
            "original_os_environ_get": original_os_environ_get # Pass original getter
        }

# --- Test Cases ---

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_success_defaults_no_creds(mock_dependencies, capsys):
    """Test main() runs successfully with defaults, but no Cloudflare creds (default mock)."""
    mocks = mock_dependencies
    # Simulate missing Cloudflare creds for this default test
    original_getter = mocks["original_os_environ_get"]
    mocks["env_get"].side_effect = (
        lambda key, default=None: None if key.startswith('CLOUDFLARE_') else original_getter(key, default)
    )

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    expected_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mocks["groq_data"]]

    test_args = ["src/main.py"] # Just the script name
    with patch.object(sys, 'argv', test_args):
        main.main()

    mocks["process"].assert_called_once_with(input_file_path=config.INPUT_WORDS_FILE)
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines, # Should be original lines as no image gen
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True, # Default is True
        original_words=expected_original_words # Check original words are passed
    )
    mocks["mkdir"].assert_not_called() # Image dir not created if no creds
    mocks["gen_image"].assert_not_called()
    mocks["is_dir"].assert_not_called() # Default anki_media_path is None
    mocks["exit"].assert_not_called()
    captured = capsys.readouterr()
    assert "Cloudflare credentials (CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN) not found" in captured.out
    assert "Skipping image generation" in captured.out
    assert "Anki Card Generation Finished" in captured.out
    assert "Anki media sync directory: Not specified" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_success_custom_args_no_audio(mock_dependencies, tmp_path, capsys):
    """Test main() with custom input/output, no audio, and valid anki media path."""
    mocks = mock_dependencies
    # Simulate missing Cloudflare creds for this test as well, focus is on other args
    original_getter = mocks["original_os_environ_get"]
    mocks["env_get"].side_effect = (
        lambda key, default=None: None if key.startswith('CLOUDFLARE_') else original_getter(key, default)
    )

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

    mocks["process"].assert_called_once_with(input_file_path=custom_input)
    mocks["write"].assert_called_once_with(
        formatted_lines=mocks["process"].return_value[0], # Original formatted lines
        output_file_path=custom_output,
        generate_audio_flag=False, # --no-audio flag was set
        original_words=expected_original_words # Check original words are passed
    )
    mocks["is_dir"].assert_called_once_with() # Called to check the media path
    assert config.ANKI_MEDIA_DIR == custom_media # Check config was updated
    mocks["exit"].assert_not_called()
    captured = capsys.readouterr()
    assert "Skipping image generation" in captured.out # Should still skip
    assert "Anki Card Generation Finished" in captured.out
    assert f"Anki media sync directory: {custom_media}" in captured.out


def test_main_missing_api_key(mock_dependencies, capsys):
    """Test main() exits if GROQ_API_KEY is not set."""
    mocks = mock_dependencies
    # Ensure key is NOT in env (handled by fixture)
    
    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mocks["exit"].assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error: Groq API key not found" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_invalid_anki_media_path(mock_dependencies, tmp_path, capsys):
    """Test main() warns and proceeds if --anki-media-path is invalid."""
    mocks = mock_dependencies
    mocks["is_dir"].return_value = False # Simulate path is not a directory
    # Simulate missing Cloudflare creds for simplicity
    original_getter = mocks["original_os_environ_get"]
    mocks["env_get"].side_effect = (
        lambda key, default=None: None if key.startswith('CLOUDFLARE_') else original_getter(key, default)
    )

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    expected_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mocks["groq_data"]]

    invalid_media_path = tmp_path / "non_existent_media"
    
    test_args = [
        "src/main.py",
        "--anki-media-path", str(invalid_media_path)
    ]
    with patch.object(sys, 'argv', test_args):
        main.main()

    # Should still proceed with generation
    mocks["process"].assert_called_once()
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines,
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    mocks["is_dir"].assert_called_once_with() # Checked the path
    assert config.ANKI_MEDIA_DIR is None # Config should remain None
    mocks["exit"].assert_not_called() # Should not exit due to invalid path
    captured = capsys.readouterr()
    assert f"Warning: Anki media path provided does not exist or is not a directory: {invalid_media_path}" in captured.out
    assert "Audio files will be generated but not copied." in captured.out
    assert "Anki media sync directory: Not specified or path invalid." in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_groq_processing_error(mock_dependencies, capsys):
    """Test main() exits if groq_generator.process_words_file raises error."""
    mocks = mock_dependencies
    mocks["process"].side_effect = Exception("Groq API Failed")
    
    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mocks["process"].assert_called_once()
    mocks["exit"].assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error during Groq API processing: Groq API Failed" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_groq_returns_no_data(mock_dependencies, capsys):
    """Test main() exits if groq_generator.process_words_file returns empty data."""
    mocks = mock_dependencies
    mocks["process"].return_value = ([], []) # Simulate no data processed
    
    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mocks["process"].assert_called_once()
    mocks["exit"].assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error: No data was processed by Groq." in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_anki_generation_error(mock_dependencies, capsys):
    """Test main() exits if anki_generator.write_anki_deck raises error."""
    mocks = mock_dependencies
    mocks["write"].side_effect = Exception("Anki Write Failed")
    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    # Simulate missing Cloudflare creds for simplicity
    original_getter = mocks["original_os_environ_get"]
    mocks["env_get"].side_effect = (
        lambda key, default=None: None if key.startswith('CLOUDFLARE_') else original_getter(key, default)
    )
    expected_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mocks["groq_data"]]

    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mocks["process"].assert_called_once()
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines,
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    mocks["exit"].assert_called_once_with(1)
    captured = capsys.readouterr()
    assert "Error during Anki deck generation: Anki Write Failed" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}) # Groq key needed
def test_main_success_with_images(mock_dependencies, capsys):
    """Test successful run with image generation (default paths, mocked creds)."""
    mocks = mock_dependencies
    # Mocks setup in fixture: env_get returns creds, gen_image returns b64

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    # Expected lines should now have the image tag prepended
    expected_formatted_lines = []
    for item in mocks["groq_data"]:
        safe_filename = "".join(c if c.isalnum() else '_' for c in item.get('word', '')) + ".png"
        img_tag = f'<img src="{safe_filename}">'
        original_line = f"{item['word_translation']};{item['german_sentence']}"
        english_part, german_part = original_line.split(';', 1)
        expected_formatted_lines.append(f"{img_tag}<br>{english_part};{german_part}")

    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    # Assertions
    # Check that the relevant keys were fetched (actual call might not include default None)
    mocks["env_get"].assert_any_call("CLOUDFLARE_ACCOUNT_ID")
    mocks["env_get"].assert_any_call("CLOUDFLARE_API_TOKEN")
    mocks["mkdir"].assert_called_once_with(parents=True, exist_ok=True)
    assert mocks["gen_image"].call_count == len(mocks["groq_data"])
    # Check open was called for writing images (adjust expected count based on groq_data)
    image_write_calls = [c for c in mocks["open"].call_args_list if c.args[1] == 'wb']
    assert len(image_write_calls) == len(mocks["groq_data"])
    mocks["b64decode"].assert_called()
    mocks["copy2"].assert_not_called() # No media path specified
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines,
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    mocks["exit"].assert_not_called()
    captured = capsys.readouterr()
    assert "Cloudflare credentials found" in captured.out
    assert "Generating Images" in captured.out
    assert "Image saved to:" in captured.out # Check for save message
    assert "Anki Card Generation Finished" in captured.out


@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_success_with_images_and_media_path(mock_dependencies, tmp_path, capsys):
    """Test successful run with image generation and copying to media path."""
    mocks = mock_dependencies
    custom_media = tmp_path / "my_media"
    custom_media.mkdir()

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    expected_formatted_lines_with_img = []
    expected_copy_calls = []
    for item in mocks["groq_data"]:
        safe_filename = "".join(c if c.isalnum() else '_' for c in item.get('word', '')) + ".png"
        img_tag = f'<img src="{safe_filename}">'
        original_line = f"{item['word_translation']};{item['german_sentence']}"
        english_part, german_part = original_line.split(';', 1)
        expected_formatted_lines_with_img.append(f"{img_tag}<br>{english_part};{german_part}")
        # Expected source path for copy
        src_img_path = config.IMAGE_OUTPUT_DIR / safe_filename
        dest_img_path = custom_media / safe_filename
        expected_copy_calls.append(call(src_img_path, dest_img_path))

    test_args = ["src/main.py", "--anki-media-path", str(custom_media)]
    with patch.object(sys, 'argv', test_args):
        main.main()

    # mkdir is called for custom_media in test setup, and for IMAGE_OUTPUT_DIR in main
    mocks["mkdir"].assert_any_call(parents=True, exist_ok=True) # Check the call from main() was made
    assert mocks["gen_image"].call_count == len(mocks["groq_data"])
    # Check open was called for writing images
    image_write_calls = [c for c in mocks["open"].call_args_list if c.args[1] == 'wb']
    assert len(image_write_calls) == len(mocks["groq_data"])
    mocks["is_dir"].assert_called_once() # Checks the media path
    assert config.ANKI_MEDIA_DIR == custom_media
    # Check copy was called for each image
    mocks["copy2"].assert_has_calls(expected_copy_calls, any_order=False)
    assert mocks["copy2"].call_count == len(mocks["groq_data"])

    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines_with_img,
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    mocks["exit"].assert_not_called()
    captured = capsys.readouterr()
    assert "Image copied to Anki media:" in captured.out
    assert f"Anki media sync directory: {custom_media}" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_skip_images_no_image_flag(mock_dependencies, capsys):
    """Test image generation is skipped when --no-image flag is used."""
    mocks = mock_dependencies
    # Credentials might be present, but flag overrides

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    expected_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mocks["groq_data"]]

    test_args = ["src/main.py", "--no-image"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    mocks["gen_image"].assert_not_called()
    mocks["mkdir"].assert_not_called()
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines, # Original lines
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    captured = capsys.readouterr()
    assert "Skipping Image Generation" in captured.out

@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_image_generation_failure(mock_dependencies, capsys):
    """Test handling when generate_image_for_prompt returns None."""
    mocks = mock_dependencies
    mocks["gen_image"].return_value = None # Simulate API failure

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    # Expect original lines because image gen failed for all
    expected_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mocks["groq_data"]]

    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    assert mocks["gen_image"].call_count == len(mocks["groq_data"])
    # Check that open was NOT called for writing ('wb'), but allow input read ('r')
    open_write_calls = [c for c in mocks["open"].call_args_list if len(c.args) > 1 and c.args[1] == 'wb']
    assert not open_write_calls, f"Expected 'open' not to be called with mode 'wb', but got calls: {open_write_calls}"
    mocks["b64decode"].assert_not_called()
    mocks["copy2"].assert_not_called()
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines, # Should fall back to original
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    captured = capsys.readouterr()
    assert "Failed to generate image for" in captured.out


@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_image_save_failure(mock_dependencies, capsys):
    """Test handling when saving the image file fails."""
    mocks = mock_dependencies

    # Mock open specifically for the 'wb' call to raise an error
    original_open_side_effect = mocks["open"].side_effect
    def failing_open_side_effect(file, mode='r', encoding=None):
        if mode == 'wb':
            raise OSError("Disk full")
        return original_open_side_effect(file, mode=mode, encoding=encoding)
    mocks["open"].side_effect = failing_open_side_effect

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    # Expect original lines because saving failed
    expected_formatted_lines = [f"{d['word_translation']};{d['german_sentence']}" for d in mocks["groq_data"]]

    test_args = ["src/main.py"]
    with patch.object(sys, 'argv', test_args):
        main.main()

    assert mocks["gen_image"].call_count == len(mocks["groq_data"])
    mocks["b64decode"].assert_called() # Decode happens before save attempt
    # Check that open was called for write binary, triggering the error
    assert any(c.args[1] == 'wb' for c in mocks["open"].call_args_list)
    mocks["copy2"].assert_not_called() # Shouldn't be called if save failed
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines, # Should fall back to original
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    captured = capsys.readouterr()
    assert "Error saving image for" in captured.out
    assert "Disk full" in captured.out # Check for the specific error message


@patch.dict(os.environ, {"GROQ_API_KEY": "test-key"})
def test_main_image_copy_failure(mock_dependencies, tmp_path, capsys):
    """Test handling when copying the image file to Anki media fails."""
    mocks = mock_dependencies
    mocks["copy2"].side_effect = shutil.Error("Permission denied")
    custom_media = tmp_path / "my_media"
    custom_media.mkdir()

    expected_original_words = [d['word'] for d in mocks["groq_data"]]
    # Expect lines *with* image tags, as saving succeeded but copy failed
    expected_formatted_lines_with_img = []
    for item in mocks["groq_data"]:
        safe_filename = "".join(c if c.isalnum() else '_' for c in item.get('word', '')) + ".png"
        img_tag = f'<img src="{safe_filename}">'
        original_line = f"{item['word_translation']};{item['german_sentence']}"
        english_part, german_part = original_line.split(';', 1)
        expected_formatted_lines_with_img.append(f"{img_tag}<br>{english_part};{german_part}")

    test_args = ["src/main.py", "--anki-media-path", str(custom_media)]
    with patch.object(sys, 'argv', test_args):
        main.main()

    assert mocks["gen_image"].call_count == len(mocks["groq_data"])
    # Check that open was called for write binary
    assert any(c.args[1] == 'wb' for c in mocks["open"].call_args_list)
    mocks["copy2"].assert_called() # Copy was attempted
    mocks["write"].assert_called_once_with(
        formatted_lines=expected_formatted_lines_with_img, # Still includes img tag
        output_file_path=config.ANKI_OUTPUT_FILE,
        generate_audio_flag=True,
        original_words=expected_original_words
    )
    captured = capsys.readouterr()
    assert "Warning: Failed to copy image to Anki media directory" in captured.out
    assert "Permission denied" in captured.out # Check for the specific error
