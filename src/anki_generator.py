import os
from tqdm import tqdm
from . import config, nlp_utils, translation, audio, data_loader

# Load data once when the module is imported
# Handle potential errors during initial data loading
try:
    GERMAN_TO_ENG_EXAMPLES, _, _ = data_loader.load_pickle_data()
except Exception as e:
    print(f"Fatal Error: Could not load initial example data. {e}")
    GERMAN_TO_ENG_EXAMPLES = [] # Ensure it's defined even on error

def get_german_example(german_word):
    """Finds a German example sentence and its English translation."""
    if not GERMAN_TO_ENG_EXAMPLES:
        return "", "" # No examples loaded

    # Ensure the word has spaces around it for more accurate matching
    german_word_spaced = f" {german_word.lower()} "
    for de_sentence, eng_translation in GERMAN_TO_ENG_EXAMPLES:
        # Check length and if the specific word is present
        if len(de_sentence.split(" ")) < config.MAX_EXAMPLE_SENTENCE_LENGTH and german_word_spaced in f" {de_sentence.lower()} ":
            return f"<br> {de_sentence}", f"<br> {eng_translation}"
    return "", ""

def _clean_german_word(word):
    """Removes common German articles and leading/trailing spaces."""
    cleaned = word.strip().lower()
    articles = ["der ", "die ", "das "]
    for article in articles:
        if cleaned.startswith(article):
            cleaned = cleaned[len(article):]
            break
    return cleaned

def generate_anki_cards(input_file_path=config.INPUT_WORDS_FILE,
                          output_file_path=config.ANKI_OUTPUT_FILE,
                          generate_audio_flag=True):
    """Processes a list of German words and generates an Anki import file."""
    print(f"Starting Anki card generation from: {input_file_path}")
    print(f"Output will be saved to: {output_file_path}")
    if not generate_audio_flag:
        print("Audio generation is disabled.")

    try:
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error creating output directory {output_file_path.parent}: {e}")
        return

    processed_count = 0
    skipped_count = 0

    try:
        with open(input_file_path, 'r', encoding='utf-8') as infile, \
             open(output_file_path, 'w', encoding='utf-8') as outfile:

            lines = infile.readlines()
            for line_num, line in enumerate(tqdm(lines, desc="Processing words", unit=" words"), 1):
                line = line.strip()
                if not line:
                    continue

                parts = [p.strip() for p in line.split(";")]
                if not parts or not parts[0]:
                    print(f"Warning: Skipping line {line_num} (empty or missing German word).")
                    skipped_count += 1
                    continue

                german_word_original = parts[0]

                # 1. Generate Audio (conditionally)
                audio_tag = ""
                if generate_audio_flag:
                    audio_tag = audio.generate_audio(german_word_original)
                # else: audio_tag remains ""

                # 2. Translate
                english_translation = translation.translate_to_english(german_word_original)
                if not english_translation:
                    print(f"Warning: Skipping '{german_word_original}' (line {line_num}) due to translation error.")
                    skipped_count += 1
                    continue

                # 3. NLP Processing
                german_word_cleaned = _clean_german_word(german_word_original)
                word_type = nlp_utils.get_german_word_type(german_word_cleaned)

                # 4. Handle Examples
                de_sentence, eng_sentence = "", ""
                if len(parts) > 2 and parts[1] and parts[2]:
                    de_sentence = f"<br> {parts[1]}"
                    eng_sentence = f"<br> {parts[2]}"
                else:
                    de_sentence, eng_sentence = get_german_example(german_word_cleaned)

                # 5. Get Plural/Display Form
                plural = ""
                german_word_display = german_word_original
                if word_type == "noun":
                    german_word_display, plural = nlp_utils.get_plural(german_word_cleaned)

                # 6. Format Output Fields
                field1 = f"{english_translation}{eng_sentence}"
                field2 = f"{german_word_display}{plural}{(' ' + audio_tag) if audio_tag else ''}{de_sentence}"

                output_line = f"{field1};{field2}"
                outfile.write(output_line + '\n')
                processed_count += 1

        print(f"\nAnki file generation complete: {output_file_path}")
        print(f"Successfully processed: {processed_count} words.")
        print(f"Skipped: {skipped_count} words.")

    except FileNotFoundError:
        print(f"Fatal Error: Input file not found at {input_file_path}")
    except IOError as e:
        print(f"Fatal Error: Could not read/write file: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during Anki generation: {e}")
        import traceback
        traceback.print_exc() 