# Anki German Word Card Generator

A Python script to automatically generate Anki flashcards for German words using the Groq API.
It generates English translations, example sentences, noun genders/plurals, conjugation info (for verbs), related words, audio pronunciation, and images.

## Features

*   **Groq API Integration**: Uses Groq (`eta-llama/llama-4-maverick-17b-128e-instruct`) to generate comprehensive linguistic information for each German word (translation, examples, grammar, etc.).
*   **Noun Processing**: Retrieves noun gender (using colored HTML: Der, Die, Das) and plural forms.
*   **Verb Processing**: Retrieves conjugation (Präsens, Perfekt, Präteritum) and case information.
*   **Audio Generation**: Generates German audio pronunciation using Google Text-to-Speech (`gTTS`).
*   **Image Generation**: Creates relevant images for words using Cloudflare AI.
*   **Anki Format**: Formats output into a semicolon-separated text file (`.txt`) suitable for direct import into Anki, including `[sound:... ]` and `<img>` tags.
*   **Media Sync**: Automatically copies generated audio and image files to a specified Anki `collection.media` directory (if configured via command-line argument).
*   **CLI**: Simple command-line interface for specifying input/output files and options.
*   **Resume Support**: Automatically resumes from where it left off if interrupted.
*   **Error Handling**: Robust error handling with retries for API calls and graceful failure recovery.
*   **Environment Configuration**: Uses `.env` file for API keys and configuration.

## Project Structure

```
anki_generator/
├── data/                  # Input data files
│   └── new_words.txt      # Default input word list (one word per line)
├── src/                   # Source code
│   ├── __init__.py
│   ├── app.py            # Main application class
│   ├── config.py         # Configuration management
│   ├── word_processor.py # Word processing logic
│   ├── word_provider.py  # Word input and filtering
│   ├── llm_generator.py  # LLM API interaction
│   ├── audio_generator.py # Audio generation
│   ├── image_generator.py # Image generation
│   └── main.py           # CLI entry point
├── tests/                # Test files
│   ├── test_app.py
│   ├── test_config.py
│   ├── test_word_processor.py
│   ├── test_word_provider.py
│   ├── test_llm_generator.py
│   ├── test_audio.py
│   └── test_image.py
├── anki_output/          # Generated output (ignored by Git)
│   ├── anki.txt         # Default output deck file
│   ├── audio/           # Generated audio files (.mp3)
│   └── images/          # Generated image files (.png)
├── .env                 # Environment variables (ignored by Git)
├── .gitattributes       # Git attributes
├── .gitignore          # Git ignore rules
├── LICENSE             # Project License
├── README.md           # This file
└── requirements.txt    # Python dependencies
```

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd anki_generator
    ```

2.  **Create and activate a virtual environment (recommended):**
    *   Using `venv`:
        ```bash
        python -m venv .venv
        source .venv/bin/activate  # Linux/macOS
        # .venv\Scripts\activate  # Windows
        ```
    *   Or using `conda`:
        ```bash
        conda create -n anki_gen python=3.10
        conda activate anki_gen
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    Create a `.env` file in the project root with the following variables:
    ```bash
    GROQ_API_KEY=your_api_key_here
    CLOUDFLARE_ACCOUNT_ID=your_account_id
    CLOUDFLARE_API_TOKEN=your_api_token
    ```
    *   **Groq API Key** (Required):
        *   Sign up at [groq.com](https://console.groq.com/keys)
    *   **Cloudflare API Keys** (Optional, for image generation):
        *   Sign up at [cloudflare.com](https://dash.cloudflare.com)

5.  **Prepare Input File:**
    *   Create or edit a text file (e.g., `data/new_words.txt`) with one German word or phrase per line.
        ```
        Aufbewahren
        Anglist
        der Tisch
        schön
        ```

## Usage

Run the script from the project's root directory:

```bash
conda activate <your_env_name> # Or source .venv/bin/activate
python src/main.py [OPTIONS]
```

**Options:**

*   `-i PATH`, `--input PATH`:
    Path to the input file containing German words (one per line).
    *Default: `data/new_words.txt`*
*   `-o PATH`, `--output PATH`:
    Path to save the generated Anki import file (`.txt`).
    *Default: `anki_output/anki.txt`*
*   `--no-audio`:
    Disable audio generation and copying to the Anki media folder.
*   `--no-image`:
    Disable image generation and copying to the Anki media folder.
*   `--anki-media-path PATH`:
    Specify the **full, absolute path** to your Anki profile's `collection.media` folder.
    If provided and valid, generated `.mp3` and `.png` files will be copied here automatically.
    *Example (Linux):* `~/.local/share/Anki2/YourProfileName/collection.media`
    *Example (Windows):* `C:\Users\YourUser\AppData\Roaming\Anki2\YourProfileName\collection.media`

**Examples:**

*   **Generate cards using default input/output:**
    ```bash
    python src/main.py
    ```
*   **Specify input and output files:**
    ```bash
    python src/main.py --input data/my_words.txt --output anki_output/my_deck.txt
    ```
*   **Generate without audio or images:**
    ```bash
    python src/main.py --no-audio --no-image
    ```
*   **Generate and sync media to Anki:**
    ```bash
    python src/main.py --anki-media-path /home/user/.local/share/Anki2/MyProfile/collection.media
    ```

## Output Format

The output file (`anki_output/anki.txt` by default) is a semicolon-separated file ready for Anki import.

*   **Field 1 (Front):** English translation(s) and example sentence translation.
*   **Field 2 (Back):** `<img>` tag (if images enabled), `[sound:word.mp3]` tag (if audio enabled), German word/phrase with grammatical info (colored article, plural, conjugation, case), example sentence, related words, additional info.

**Example Line (for 'der Tisch'):**

```
table; a piece of furniture with a flat top and one or more legs<br>The table is in the kitchen.;<img src='Tisch.png'>[sound:Tisch.mp3]<span style="color: rgb(10, 2, 255)">Der</span> Tisch (die Tische)<br>Der Tisch steht in der Küche.<br>Related: Stuhl (chair), Möbel (furniture), Esstisch (dining table)<br>Info: Masculine noun.
```

## Anki Import

1.  Open Anki.
2.  Go to `File > Import...`.
3.  Select the generated `.txt` file (e.g., `anki_output/anki.txt`).
4.  Configure the import settings:
    *   Choose or create an appropriate Note Type (e.g., Basic).
    *   **Fields separated by:** Semicolon
    *   **Allow HTML in fields:** Check this box.
    *   Map **Field 1** to the Front template field.
    *   Map **Field 2** to the Back template field.
5.  Click `Import`.

## Testing

The project includes a comprehensive test suite for all major components. Tests are organized by module in the `tests` directory:

- `test_config.py`: Tests for configuration management
- `test_word_processor.py`: Tests for word processing functionality
- `test_word_provider.py`: Tests for word input and filtering
- `test_app.py`: Tests for the main application class
- `test_llm_generator.py`: Tests for LLM-based text generation
- `test_audio.py`: Tests for audio generation
- `test_image.py`: Tests for image generation

### Running Tests

To run the tests, use pytest:

```bash
# Run all tests
pytest

# Run tests for a specific module
pytest tests/test_config.py

# Run tests with verbose output
pytest -v

# Run tests with coverage report
pytest --cov=src
```

### Test Coverage

The test suite provides comprehensive coverage of:
- Configuration management and validation
- Word processing and formatting
- Input/output file handling
- Error handling and edge cases
- Integration between components

Each test file includes:
- Fixtures for common test setup
- Tests for success and failure cases
- Mock objects for external dependencies
- Clear documentation of test purposes

## Dependencies

*   `groq==0.22.0`: For accessing the Groq API.
*   `gTTS==2.5.4`: For text-to-speech audio generation.
*   `german-nouns==1.2.5`: For noun gender and plural lookup.
*   `deep-translator==1.11.4`: For fallback translation.
*   `tqdm==4.67.1`: For progress bars.
*   `requests`: For API calls.
*   `python-dotenv`: For environment variable management.
*   `pytest` and `pytest-mock`: For testing.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 