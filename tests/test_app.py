import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from contextlib import nullcontext
from unittest.mock import call

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the module under test
from src.app import AnkiGeneratorApp

# --- Fixtures ---

@pytest.fixture
def mock_args():
    """Creates a mock args object with default values."""
    args = MagicMock()
    args.input = Path("input.txt")
    args.output = Path("output.txt")
    args.no_audio = False
    args.no_image = False
    args.anki_media_path = None
    return args

@pytest.fixture
def mock_word_provider():
    """Creates a mock WordProvider instance."""
    provider = MagicMock()
    provider.get_words.return_value = iter(["Haus", "Auto"])
    provider.__len__.return_value = 2
    provider.get_file_mode.return_value = 'w'
    return provider

@pytest.fixture
def mock_managed_output_file():
    """Creates a mock context manager for file handling."""
    mock_file = MagicMock()
    mock_file.write = MagicMock()
    mock_cm = MagicMock()
    mock_cm.__enter__ = MagicMock(return_value=mock_file)
    mock_cm.__exit__ = MagicMock(return_value=None)
    return mock_cm

@pytest.fixture
def mock_word_processor():
    """Creates a mock WordProcessor instance."""
    processor = MagicMock()
    processor.process_word.side_effect = [
        "house;[sound:Haus.mp3]Haus",
        "car;[sound:Auto.mp3]Auto"
    ]
    return processor

@pytest.fixture
def app():
    """Creates an AnkiGeneratorApp instance."""
    return AnkiGeneratorApp()

# --- Tests for _parse_arguments ---

@patch('argparse.ArgumentParser.parse_args')
def test_parse_arguments_defaults(mock_parse_args, app, mock_args):
    """Test argument parsing with default values."""
    mock_parse_args.return_value = mock_args
    
    app._parse_arguments()
    
    assert app.args == mock_args
    mock_parse_args.assert_called_once()

# --- Tests for _setup ---

@patch('src.app.WordProcessor')
@patch('src.app.WordProvider')
@patch('src.config.check_prerequisites')
@patch('src.config.setup_config')
def test_setup_success(mock_setup_config, mock_check_prerequisites, mock_word_provider_class, 
                      mock_word_processor_class, mock_args):
    """Test successful setup."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    
    # Configure mocks
    mock_check_prerequisites.return_value = (True, True)
    mock_word_provider = MagicMock()
    mock_word_processor = MagicMock()
    mock_word_provider_class.return_value = mock_word_provider
    mock_word_processor_class.return_value = mock_word_processor
    
    # Run setup
    app._setup()
    
    # Verify
    mock_setup_config.assert_called_once_with(app.args)
    mock_check_prerequisites.assert_called_once_with(app.args)
    mock_word_provider_class.assert_called_once_with(app.args.input, app.args.output)
    mock_word_processor_class.assert_called_once_with(app.args, True)
    assert app.word_provider == mock_word_provider
    assert app.word_processor == mock_word_processor

@patch('src.config.check_prerequisites')
@patch('src.config.setup_config')
def test_setup_prerequisites_failed(mock_setup_config, mock_check_prerequisites, mock_args):
    """Test setup when prerequisites check fails."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    
    # Configure mock to indicate prerequisites failure
    mock_check_prerequisites.return_value = (False, False)
    
    with pytest.raises(SystemExit):
        app._setup()
    
    mock_setup_config.assert_called_once_with(app.args)
    mock_check_prerequisites.assert_called_once_with(app.args)

# --- Tests for _managed_output_file ---

@patch('builtins.open', new_callable=mock_open)
def test_managed_output_file_success(mock_open_func, mock_args):
    """Test successful file management."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    app.word_provider = MagicMock()
    app.word_provider.get_file_mode.return_value = 'w'

    with app._managed_output_file() as f:
        assert f == mock_open_func.return_value
        mock_open_func.assert_called_once_with(mock_args.output, 'w', encoding='utf-8')

@patch('builtins.open', new_callable=mock_open)
def test_write_output_line_success(mock_open_func, mock_args):
    """Test writing a line to the output file."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    mock_file = mock_open_func.return_value
    app.output_file = mock_file

    app._write_output_line("test line")
    mock_file.write.assert_called_once_with("test line\n")

def test_write_output_line_no_file(mock_args):
    """Test writing a line when no file is open."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    app.output_file = None

    with pytest.raises(RuntimeError):
        app._write_output_line("test line")

# --- Tests for _run_processing_loop ---

@patch('builtins.open', new_callable=mock_open)
def test_run_processing_loop_success(mock_open_func, mock_args, mock_word_provider, mock_word_processor):
    """Test successful word processing loop."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    app.word_provider = mock_word_provider
    app.word_processor = mock_word_processor
    mock_file = mock_open_func.return_value
    app.output_file = mock_file

    # Configure mocks
    mock_word_provider.get_words.return_value = iter(["Haus", "Auto"])
    mock_word_processor.process_word.side_effect = ["Line 1", "Line 2"]
    
    app._run_processing_loop()
    
    assert app.successful_words == 2
    assert app.failed_words == 0
    assert mock_word_processor.process_word.call_count == 2
    mock_file.write.assert_has_calls([
        call("Line 1\n"),
        call("Line 2\n")
    ])

@patch('builtins.open', new_callable=mock_open)
def test_run_processing_loop_with_failures(mock_open_func, mock_args, mock_word_provider, mock_word_processor):
    """Test processing loop with some failures."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    app.word_provider = mock_word_provider
    app.word_processor = mock_word_processor
    mock_file = mock_open_func.return_value
    app.output_file = mock_file

    # Configure mocks
    mock_word_provider.get_words.return_value = iter(["Haus", "Auto"])
    mock_word_processor.process_word.side_effect = [None, "Line 2"]  # First word fails
    
    app._run_processing_loop()
    
    assert app.successful_words == 1
    assert app.failed_words == 1
    assert mock_word_processor.process_word.call_count == 2
    mock_file.write.assert_called_once_with("Line 2\n")

@patch('builtins.open', new_callable=mock_open)
def test_run_processing_loop_no_words(mock_open_func, mock_args, mock_word_provider):
    """Test processing loop with no words to process."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    app.word_provider = mock_word_provider
    mock_file = mock_open_func.return_value
    app.output_file = mock_file
    
    # Configure mock to return empty iterator
    mock_word_provider.get_words.return_value = iter([])
    
    app._run_processing_loop()
    
    assert app.successful_words == 0
    assert app.failed_words == 0
    mock_file.write.assert_not_called()

# --- Tests for _print_summary ---

@patch('builtins.print')
def test_print_summary_success(mock_print, app, mock_args):
    """Test successful summary printing."""
    app.args = mock_args
    app.successful_words = 2
    app.failed_words = ["Auto"]
    
    app._print_summary()
    
    assert mock_print.call_count >= 3  # At least 3 print calls (header, success, failure)
    mock_print.assert_any_call("Successfully processed: 2 words")
    mock_print.assert_any_call("Failed to process: 1 words: ['Auto']")

def test_print_summary(mock_args, capsys):
    """Test summary printing."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    app.successful_words = 5
    app.failed_words = 2
    
    app._print_summary()
    
    captured = capsys.readouterr()
    assert "Successfully processed 5 words" in captured.out
    assert "Failed to process 2 words" in captured.out

# --- Tests for run ---

@patch('src.app.AnkiGeneratorApp._setup')
@patch('src.app.AnkiGeneratorApp._run_processing_loop')
@patch('src.app.AnkiGeneratorApp._print_summary')
def test_run_success(mock_print_summary, mock_run_loop, mock_setup, app):
    """Test successful application run."""
    app.run()
    
    mock_setup.assert_called_once()
    mock_run_loop.assert_called_once()
    mock_print_summary.assert_called_once()

def test_setup_success(mock_args, mock_word_provider, mock_word_processor):
    """Test successful setup."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    
    app._setup()
    
    assert isinstance(app.word_provider, MagicMock)
    assert isinstance(app.word_processor, MagicMock)

def test_setup_failure(mock_args):
    """Test setup with failure."""
    app = AnkiGeneratorApp()
    app.args = mock_args
    
    # Simulate failure in prerequisites check
    with patch.object(app, '_check_prerequisites', side_effect=Exception("Setup failed")):
        with pytest.raises(SystemExit):
            app._setup()

def test_parse_arguments(monkeypatch):
    """Test argument parsing."""
    test_args = ['--input', 'input.txt', '--output', 'output.txt']
    monkeypatch.setattr('sys.argv', ['script.py'] + test_args)
    
    app = AnkiGeneratorApp()
    args = app._parse_arguments()
    
    assert args.input == Path('input.txt')
    assert args.output == Path('output.txt')
    assert not args.no_audio
    assert not args.no_image
    assert args.anki_media_path is None 