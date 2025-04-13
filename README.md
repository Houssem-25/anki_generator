# Anki German Word Card Generator

This script processes a list of German words (and optional example sentences) from a text file, translates them to English, finds noun genders and plurals, generates audio pronunciation, and formats the data into a text file suitable for importing into Anki.

## Features

- Translates German words to English using Google Translate.
- Retrieves noun gender (Der/Die/Das) and plural forms using `german-nouns`.
- Parses words to identify type (noun, verb, adjective) using `pattern.de`.
- Generates German audio pronunciation using Google Text-to-Speech (gTTS).
- Fetches example sentences from a pre-existing corpus (if not provided in the input file).
- Copies generated audio files to the Anki media collection folder (requires configuration).
- Outputs data in a semicolon-separated format for easy Anki import.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Houssem-25/anki_generator.git
    cd anki_generator
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **(Optional) Download `pattern.de` models:** The `pattern.de` library might require downloading language models the first time it's used. The script includes a warmup function, but you might need an internet connection when running it initially.
5.  **(Optional) Prepare `german_to_eng.pickle`:** This script assumes a `german_to_eng.pickle` file exists, containing a list of German-English sentence pairs. You'll need to provide or generate this file.
6.  **(Optional) Configure Anki Media Path:** The `copy_to_anki_media` function tries to copy audio files to the default Anki media path using `os.getenv('APPDATA')`. This might need adjustment depending on your operating system (Linux/macOS) and Anki profile name. Edit the `anki_media_dir` variable in `main.py` if necessary.

## Usage

1.  **Prepare your input file:** Create a text file (e.g., `new_words.txt`) with one German word per line.
    *   Format: `GermanWord`
    *   Alternatively, provide the word and example sentences: `GermanWord;German Sentence;English Translation`
2.  **Run the script:**
    ```bash
    python main.py
    ```
    *   Make sure your input file is named `new_words.txt` or change the `file_path` variable in the `if __name__ == "__main__":` block.
3.  **Import into Anki:**
    *   The script will generate an `anki/anki.txt` file.
    *   Open Anki, go to `File -> Import...`, and select `anki/anki.txt`.
    *   Ensure the fields map correctly (Field 1 -> Front, Field 2 -> Back, separator -> Semicolon).
    *   Make sure "Allow HTML in fields" is checked.

## Files

-   `main.py`: The main Python script.
-   `new_words.txt`: Example input file (you should create your own).
-   `requirements.txt`: Project dependencies.
-   `german_to_eng.pickle`: (Required) Pickle file containing German-English sentence pairs.
-   `german_to_eng_ids.pickle`: (Required) Associated IDs for the sentence pairs.
-   `new_english_texts.pickle`: (Required) Pickle file with English texts.
-   `anki/`: Directory where output (`anki.txt`) and generated audio files (`.mp3`) are stored.
-   `.gitignore`: Specifies intentionally untracked files for Git.
-   `LICENSE`: Project license (MIT).

## Dependencies

-   `deep_translator`
-   `pattern.de`
-   `german_nouns`
-   `gTTS`
-   `tqdm` 