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
            return f"<br>  {de_sentence}", f"<br>  {eng_translation}"
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

                # 2. Get translations and sentences
                # Since we've made Groq the default, we assume input has 3 parts: word, sentence, translation
                if len(parts) >= 3:
                    de_sentence = parts[1].strip()
                    eng_translation = parts[2].strip()
                else:
                    # Fallback to traditional method for non-Groq inputs
                    eng_translation = translation.translate_to_english(german_word_original)
                    if not eng_translation:
                        print(f"Warning: Skipping '{german_word_original}' (line {line_num}) due to translation error.")
                        skipped_count += 1
                        continue
                    
                    # Use traditional example finding
                    temp_de_sentence, _ = get_german_example(german_word_cleaned)
                    de_sentence = temp_de_sentence.replace("<br>  ", "").strip()

                # 3. NLP Processing
                german_word_cleaned = _clean_german_word(german_word_original)
                word_type = nlp_utils.get_german_word_type(german_word_cleaned)
                print(f"Word: {german_word_cleaned} - Type: {word_type}")
                
                # Manual article detection as fallback
                original_has_article = any(german_word_original.lower().startswith(article.lower()) 
                                          for article in ["der ", "die ", "das "])
                first_char_uppercase = german_word_original[0].isupper() if german_word_original else False
                
                # If it's a capitalized word or has an article, it's likely a noun in German
                if word_type == "unknown" and (original_has_article or first_char_uppercase):
                    print(f"Fallback: Treating '{german_word_original}' as a noun based on capitalization/article")
                    word_type = "noun"
                    
                    # Extract the article from the original word if present
                    manual_article = ""
                    if original_has_article:
                        for article in ["Der ", "Die ", "Das "]:
                            if german_word_original.startswith(article):
                                if article == "Der ":
                                    manual_article = config.GENDER_TO_ARTICLE_HTML.get("m", "")
                                elif article == "Die ":
                                    manual_article = config.GENDER_TO_ARTICLE_HTML.get("f", "")
                                elif article == "Das ":
                                    manual_article = config.GENDER_TO_ARTICLE_HTML.get("n", "")
                                break

                # 4. Get Plural/Display Form
                plural = ""
                german_word_display = german_word_original
                
                # Store any manually detected article
                manual_article = ""
                
                # If word is a noun, get plural and article information
                if word_type == "noun":
                    # First try the NLP tools
                    temp_display, temp_plural = nlp_utils.get_plural(german_word_cleaned)
                    
                    # Clean up the plural form to remove HTML line breaks
                    if temp_plural:
                        plural = temp_plural.replace("<br>", "").strip()
                    
                    # If the NLP tools didn't add an article, check if we can add one manually
                    if not any(marker in temp_display for marker in ["Der</span>", "Die</span>", "Das</span>"]):
                        # Check for article in the original word
                        if original_has_article:
                            # Set manual article based on the original word
                            for article_text, gender in [("Der ", "m"), ("Die ", "f"), ("Das ", "n")]:
                                if german_word_original.startswith(article_text):
                                    manual_article = config.GENDER_TO_ARTICLE_HTML.get(gender, "")
                                    # Remove the article from original for cleaner display
                                    clean_word = german_word_original[len(article_text):]
                                    # Return with manual article and capitalized word
                                    german_word_display = manual_article + clean_word
                                    break
                        else:
                            # Just use the result from nlp_utils
                            german_word_display = temp_display
                    else:
                        # NLP tools added an article, use that
                        german_word_display = temp_display
                    
                    # If plural is still empty and we have a manual article, add a generic plural
                    if not plural and manual_article and 'Der</span>' in manual_article:
                        # For masculine nouns, a common plural pattern is to add "e" or "en"
                        base_word = german_word_original.replace("Der ", "").replace("der ", "")
                        plural = f"{config.GENDER_TO_ARTICLE_HTML.get('pl', '')}{base_word}e"
                        print(f"Added generic plural for '{german_word_original}': {plural}")
                
                # 5. Format Output Fields for Anki
                
                # Field 1: English Translation
                field1 = eng_translation
                
                # Field 2: Format German with better spacing, including any plurals and audio
                if word_type == "noun" and plural:
                    # Noun with plural form
                    plural_html = f" / {plural}"
                    field2 = f"{german_word_display}{plural_html} {audio_tag}"
                else:
                    # Simple word without plural
                    field2 = f"{german_word_display} {audio_tag}"
                
                # Add example sentence if available
                if de_sentence:
                    field2 += f" <br><br><i>{de_sentence}</i>"
                
                # Add final semicolon
                field2 += ";"

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