# Anki German Word Card Generator

A Python script to automatically generate Anki flashcards for German words, including English translation, example sentences, noun genders/plurals, and audio pronunciation.

## Features

*   Translates German words to English using Deep Translator (Google Translate API).
*   Retrieves noun gender (using colored articles: Der, Die, Das) and plural forms using the `german-nouns` library.
*   Attempts to find example German sentences and their English translations from provided data.
*   **NEW**: Uses Groq API (LLM) to generate contextually relevant German example sentences and English translations.
*   Generates German audio pronunciation using Google Text-to-Speech (gTTS).
*   Formats output into a semicolon-separated text file (`.txt`) suitable for direct import into Anki.
*   Automatically copies generated audio files to a specified Anki media directory (if configured).
*   Command-line interface for specifying input/output files and options.

## Project Structure

```
anki_generator/
├── data/                  # Input data files (ignored by Git)
│   ├── german_to_eng.pickle
│   ├── german_to_eng_ids.pickle
│   ├── new_english_texts.pickle
│   └── new_words.txt      # Default input word list
├── src/                   # Source code
│   ├── __init__.py
│   ├── anki_generator.py  # Core card generation logic
│   ├── audio.py           # Audio generation and copying
│   ├── config.py          # Configuration constants and paths
│   ├── data_loader.py     # Loads data files
│   ├── groq_generator.py  # NEW: Groq API integration for example generation
│   ├── main.py            # Main script entry point (CLI)
│   ├── nlp_utils.py       # German NLP functions (parsing, plurals)
│   └── translation.py     # Translation functions
├── anki_output/           # Generated output (ignored by Git)
│   ├── anki.txt           # Default output file
│   └── audio/             # Generated audio files (.mp3)
├── .gitattributes         # Git attributes (line endings)
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

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Please ensure you add the correct versions for `pattern.de`, `german_nouns`, `gTTS`, `groq`, and `tqdm` in `requirements.txt` if the `pip freeze` command didn't capture them.* 

4.  **Set up Groq API (optional):**
    *   Sign up for a Groq API key at [groq.com](https://groq.com)
    *   Set your API key as an environment variable:
        ```bash
        export GROQ_API_KEY=your_api_key_here  # Linux/macOS
        # OR
        set GROQ_API_KEY=your_api_key_here     # Windows Command Prompt
        # OR
        $env:GROQ_API_KEY="your_api_key_here"  # Windows PowerShell
        ```

5.  **Prepare Input Data:**
    *   Place your input word list file (one German word or phrase per line) in the `data/` directory. The default file is `data/new_words.txt`.
    *   For the Groq API feature, the input file should only contain one German word per line without additional formatting.
    *   Ensure the example sentence data files (`german_to_eng.pickle`, etc.) are present in the `data/` directory if you rely on the automatic example finding.

## Usage

Run the script from the project's root directory:

```bash
python src/main.py [OPTIONS]
```

**Options:**

*   `-i PATH`, `--input PATH`:
    Path to the input file containing German words (one per line).
    *Default: `data/new_words.txt`*
*   `-o PATH`, `--output PATH`:
    Path to save the generated Anki import file.
    *Default: `anki_output/anki.txt`*
*   `--no-audio`:
    Disable audio generation and copying to the Anki media folder.
*   `--anki-media-path PATH`:
    Specify the path to your Anki profile's `collection.media` folder. If provided, generated `.mp3` files will be copied here automatically (unless `--no-audio` is used).
    *Default: Attempts to find path using `APPDATA` (Windows) or requires manual setting.*
*   `--use-groq`:
    Use Groq API to generate example sentences and translations for each German word.
*   `--groq-output PATH`:
    Path to save the raw output from Groq API processing (optional).
*   `--keep-groq-temp`:
    Keep the temporary file created during Groq API processing (will not be deleted after processing).

**Examples:**

*   **Generate cards using default settings:**
    ```bash
    python src/main.py
    ```
*   **Specify input and output files:**
    ```bash
    python src/main.py --input data/my_word_list.txt --output anki_output/my_deck.txt
    ```
*   **Use Groq API to generate examples and translations:**
    ```bash
    python src/main.py --use-groq
    ```
*   **Save the Groq API processed output and keep the temporary file:**
    ```bash
    python src/main.py --use-groq --groq-output data/groq_processed.txt --keep-groq-temp
    ```
*   **Generate without audio:**
    ```bash
    python src/main.py --no-audio
    ```
*   **Generate with Groq API and specify Anki media path:**
    ```bash
    python src/main.py --use-groq --anki-media-path ~/.local/share/Anki2/YourProfileName/collection.media
    ```
    *(Replace `YourProfileName` with your actual Anki profile name)*

## Input Format for Groq API Feature

When using the `--use-groq` option, your input file should contain one German word per line:

```
Aufbewahren
Anglist
Ehrendoktorwürde
```

The Groq API will generate example sentences and translations in the format:

```
Aufbewahren; Sie bewahrte die Dokumente in einer Box auf; She stored the documents in a box.
Anglist; Der Anglist unterrichtete Literatur an der Universität; The English scholar taught literature at the university.
Ehrendoktorwürde; Er erhielt die Ehrendoktorwürde für seine wissenschaftlichen Leistungen; He received an honorary doctorate for his academic achievements.
```

## Anki Import

1.  Open Anki.
2.  Go to `File > Import...`.
3.  Select the generated `.txt` file (e.g., `anki_output/anki.txt`).
4.  Configure the import settings:
    *   **Fields separated by:** Semicolon
    *   **Allow HTML in fields:** Check this box.
    *   Map the fields correctly (Field 1 -> Front, Field 2 -> Back, or as desired).
5.  Click `Import`.

## Dependencies

*   `deep-translator`: For translation.
*   `pattern.de`: For German NLP tasks (parsing, conjugation).
*   `german-nouns`: For noun gender and plural lookup.
*   `gTTS`: For text-to-speech audio generation.
*   `tqdm`: For progress bars.
*   `groq`: For accessing the Groq API to generate example sentences and translations.

See `requirements.txt` for specific versions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 