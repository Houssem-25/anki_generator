import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the module under test
from src import config

# --- Fixtures ---

@pytest.fixture
def mock_args():
    """Creates a mock args object with default values."""
    args = MagicMock()
    args.anki_media_path = None
    args.no_audio = False
    args.no_image = False
    args.output = Path("test_output.txt")
    return args

@pytest.fixture(autouse=True)
def setup_env_vars():
    """Sets up and cleans up environment variables for testing."""
    # Store original values
    original_groq_key = os.environ.get("GROQ_API_KEY")
    original_cf_account = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    original_cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    
    # Clear environment variables
    if "GROQ_API_KEY" in os.environ:
        del os.environ["GROQ_API_KEY"]
    if "CLOUDFLARE_ACCOUNT_ID" in os.environ:
        del os.environ["CLOUDFLARE_ACCOUNT_ID"]
    if "CLOUDFLARE_API_TOKEN" in os.environ:
        del os.environ["CLOUDFLARE_API_TOKEN"]
    
    yield
    
    # Restore original values
    if original_groq_key:
        os.environ["GROQ_API_KEY"] = original_groq_key
    if original_cf_account:
        os.environ["CLOUDFLARE_ACCOUNT_ID"] = original_cf_account
    if original_cf_token:
        os.environ["CLOUDFLARE_API_TOKEN"] = original_cf_token

# --- Tests for setup_config ---

def test_setup_config_no_anki_media(mock_args):
    """Test setup_config when no Anki media path is provided."""
    config.setup_config(mock_args)
    assert config.ANKI_MEDIA_DIR is None

def test_setup_config_with_valid_anki_media(mock_args, tmp_path):
    """Test setup_config with a valid Anki media path."""
    anki_media_path = tmp_path / "anki_media"
    anki_media_path.mkdir()
    mock_args.anki_media_path = anki_media_path
    
    config.setup_config(mock_args)
    assert config.ANKI_MEDIA_DIR == anki_media_path

def test_setup_config_with_invalid_anki_media(mock_args, tmp_path, capsys):
    """Test setup_config with an invalid Anki media path."""
    invalid_path = tmp_path / "nonexistent"
    mock_args.anki_media_path = invalid_path
    
    config.setup_config(mock_args)
    assert config.ANKI_MEDIA_DIR is None
    
    captured = capsys.readouterr()
    assert "Warning: Anki media path provided does not exist" in captured.out

def test_setup_config_creates_output_dirs(mock_args, tmp_path):
    """Test that setup_config creates necessary output directories."""
    mock_args.output = tmp_path / "output.txt"
    mock_args.anki_media_path = tmp_path / "anki_media"
    mock_args.anki_media_path.mkdir()
    
    config.setup_config(mock_args)
    
    assert mock_args.output.parent.exists()
    assert config.AUDIO_OUTPUT_DIR.exists()
    assert config.IMAGE_OUTPUT_DIR.exists()

# --- Tests for check_prerequisites ---

def test_check_prerequisites_no_groq_key(mock_args, capsys):
    """Test check_prerequisites when GROQ_API_KEY is missing."""
    result, can_generate_images = config.check_prerequisites(mock_args)
    assert result is False
    assert can_generate_images is False
    
    captured = capsys.readouterr()
    assert "Error: Groq API key not found" in captured.out

def test_check_prerequisites_with_groq_key(mock_args):
    """Test check_prerequisites with only GROQ_API_KEY set."""
    os.environ["GROQ_API_KEY"] = "test_key"
    result, can_generate_images = config.check_prerequisites(mock_args)
    assert result is True
    assert can_generate_images is False

def test_check_prerequisites_with_all_keys(mock_args, capsys):
    """Test check_prerequisites with all API keys set."""
    os.environ["GROQ_API_KEY"] = "test_key"
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = "test_account"
    os.environ["CLOUDFLARE_API_TOKEN"] = "test_token"
    
    result, can_generate_images = config.check_prerequisites(mock_args)
    assert result is True
    assert can_generate_images is True
    
    captured = capsys.readouterr()
    assert "Cloudflare credentials found. Image generation enabled" in captured.out

def test_check_prerequisites_no_image_flag(mock_args):
    """Test check_prerequisites when --no-image flag is set."""
    mock_args.no_image = True
    os.environ["GROQ_API_KEY"] = "test_key"
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = "test_account"
    os.environ["CLOUDFLARE_API_TOKEN"] = "test_token"
    
    result, can_generate_images = config.check_prerequisites(mock_args)
    assert result is True
    assert can_generate_images is False

def test_check_prerequisites_partial_cloudflare_creds(mock_args, capsys):
    """Test check_prerequisites with only partial Cloudflare credentials."""
    os.environ["GROQ_API_KEY"] = "test_key"
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = "test_account"
    
    result, can_generate_images = config.check_prerequisites(mock_args)
    assert result is True
    assert can_generate_images is False
    
    captured = capsys.readouterr()
    assert "Warning: Cloudflare credentials missing" in captured.out
