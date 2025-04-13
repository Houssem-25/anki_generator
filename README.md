# Anki German Word Card Generator

A Python script to automatically generate Anki flashcards for German words using the Groq API.
It generates English translations, example sentences, noun genders/plurals, conjugation info (for verbs), related words, and audio pronunciation.

## Features

*   **Groq API Integration**: Uses Groq (`llama3-8b-8192`) to generate comprehensive linguistic information for each German word (translation, examples, grammar, etc.).
*   **Noun Processing**: Retrieves noun gender (using colored HTML: Der, Die, Das) and plural forms.
*   **Verb Processing**: Retrieves conjugation (Präsens, Perfekt, Präteritum) and case information.
*   **Audio Generation**: Generates German audio pronunciation using Google Text-to-Speech (`gTTS`).
*   **Anki Format**: Formats output into a semicolon-separated text file (`.txt`) suitable for direct import into Anki, including `[sound:... ]` tags.
*   **Media Sync**: Automatically copies generated audio files to a specified Anki `collection.media` directory (if configured via command-line argument).
*   **CLI**: Simple command-line interface for specifying input/output files and options.

## Project Structure

```
anki_generator/
├── data/                  # Input data files
│   └── new_words.txt      # Default input word list (one word per line)
├── src/                   # Source code
│   ├── __init__.py
│   ├── anki_generator.py  # Anki deck (.txt) writing logic
│   ├── audio.py           # Audio generation (gTTS) and copying
│   ├── config.py          # Configuration constants and paths
│   ├── groq_generator.py  # Groq API interaction and data processing
│   └── main.py            # Main script entry point (CLI)
├── anki_output/           # Generated output (ignored by Git)
│   ├── anki.txt           # Default output deck file
│   └── audio/             # Generated audio files (.mp3)
├── .gitattributes         # Git attributes
├── .gitignore             # Git ignore rules
├── LICENSE                # Project License
├── README.md              # This file
└── requirements.txt       # Python dependencies
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
        conda create -n anki_gen python=3.10 # Or your desired version
        conda activate anki_gen
        ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up Groq API Key:**
    *   Sign up for a Groq API key at [groq.com](https://console.groq.com/keys)
    *   Set your API key as an environment variable. The script **requires** this variable to run.
        ```bash
        export GROQ_API_KEY='your_api_key_here'  # Linux/macOS
        # set GROQ_API_KEY=your_api_key_here     # Windows Command Prompt
        # $env:GROQ_API_KEY="your_api_key_here"  # Windows PowerShell
        ```

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
export GROQ_API_KEY='your_key' # Make sure key is set
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
*   `--anki-media-path PATH`:
    Specify the **full, absolute path** to your Anki profile's `collection.media` folder.
    If provided and valid, generated `.mp3` files will be copied here automatically (unless `--no-audio` is used).
    *Example (Linux):* `~/.local/share/Anki2/YourProfileName/collection.media`
    *Example (Windows):* `C:\Users\YourUser\AppData\Roaming\Anki2\YourProfileName\collection.media`
    *(Note: This path is often on a different drive or location than the project)*

**Examples:**

*   **Generate cards using default input/output:**
    ```bash
    python src/main.py
    ```
*   **Specify input and output files:**
    ```bash
    python src/main.py --input data/my_words.txt --output anki_output/my_deck.txt
    ```
*   **Generate without audio:**
    ```bash
    python src/main.py --no-audio
    ```
*   **Generate and sync audio to Anki media folder:**
    ```bash
    python src/main.py --anki-media-path /home/user/.local/share/Anki2/MyProfile/collection.media
    ```

## Output Format (`.txt` file)

The output file (`anki_output/anki.txt` by default) is a semicolon-separated file ready for Anki import.

*   **Field 1 (Front):** English translation(s) and example sentence translation.
*   **Field 2 (Back):** `[sound:word.mp3]` tag (if audio enabled), German word/phrase with grammatical info (colored article, plural, conjugation, case), example sentence, related words, additional info.

**Example Line (for 'der Tisch'):**

```
table; a piece of furniture with a flat top and one or more legs<br>The table is in the kitchen.;[sound:Tisch.mp3]<span style="color: rgb(10, 2, 255)">Der</span> Tisch (die Tische)<br>Der Tisch steht in der Küche.<br>Related: Stuhl (chair), Möbel (furniture), Esstisch (dining table)<br>Info: Masculine noun.
```

*(Actual output formatting depends on Groq API results)*

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

## Dependencies

*   `groq`: For accessing the Groq API.
*   `gTTS`: For text-to-speech audio generation.
*   `german-nouns`: For noun gender and plural lookup (used by Groq prompt generation).
*   `deep-translator`: For fallback translation (currently unused in main flow).
*   `tqdm`: For progress bars.

See `requirements.txt` for specific versions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 