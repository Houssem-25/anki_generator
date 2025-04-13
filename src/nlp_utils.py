from pattern.de import parse, conjugate
from german_nouns.lookup import Nouns
from . import config

nouns = Nouns()

def _attempt_with_retry(func, name, attempts):
    """Helper function to attempt a function call with retries."""
    for attempt in range(attempts):
        try:
            func("test")
            print(f"{name} warmed up after {attempt + 1} attempts.")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for {name}: {e}")
            continue
    print(f"Failed to warm up {name} after {attempts} attempts.")
    return False

def warmup_parser():
    """Warms up the pattern.de parser and conjugate functions."""
    print("Warming up NLP components...")
    parse_success = _attempt_with_retry(parse, "Parser", config.WARMUP_ATTEMPTS)
    conjugate_success = _attempt_with_retry(conjugate, "Conjugator", config.WARMUP_ATTEMPTS)
    if not parse_success or not conjugate_success:
        print("Warning: Failed to warm up one or more NLP components.")
    else:
        print("NLP components warmed up successfully.")

def get_german_word_type(german_word):
    """Determines the grammatical type (noun, verb, adjective) of a German word."""
    try:
        parsed = parse(german_word)
        if parsed:
            parts = parsed.split("/")
            if len(parts) > 1:
                pos_tag = parts[1]
                if pos_tag.startswith("V"):
                    return "verb"
                elif pos_tag.startswith("JJ"):
                    return "adjective" # Changed from adjectif
        # Check using german-nouns library if parsing doesn't identify it clearly
        # or if it might be a noun not caught by pattern.de's POS tagger
        if nouns and german_word in nouns and len(nouns[german_word]) > 0:
             return "noun"
    except Exception as e:
        print(f"Error determining word type for '{german_word}': {e}")
    return "unknown"

def get_plural(german_word):
    """Gets the article and plural form for a German noun."""
    plural = ""
    article = ""
    word_data_list = nouns.get(german_word, [])

    if not word_data_list:
        print(f"Warning: No data found for noun '{german_word}' in german-nouns library.")
        # Return the word capitalized as a fallback, assuming it might be a proper noun or similar
        return german_word.capitalize(), ""

    # Use the first entry if multiple exist (heuristic)
    word_data = word_data_list[0]
    flexion = word_data.get("flexion", {})
    genus_keys = [k for k in word_data if k.startswith("genus")]

    # --- Get Plural --- 
    if "nominativ plural" in flexion:
        plural = flexion["nominativ plural"]
    elif "nominativ plural 2" in flexion:
        plural = flexion["nominativ plural 2"]

    if plural:
        plural = "<br> " + config.GENDER_TO_ARTICLE_HTML.get("pl", "Die ") + plural # Use .get for safety

    # --- Get Article --- 
    if "genus" in word_data:
        article = config.GENDER_TO_ARTICLE_HTML.get(word_data["genus"], "")
    elif genus_keys: # Handle cases like 'genus 1', 'genus 2'
        articles = [config.GENDER_TO_ARTICLE_HTML.get(word_data[g], "") for g in sorted(genus_keys)]
        article = " ".join(filter(None, articles)) # Join non-empty articles
    # If no article found, maybe it's not a typical noun requiring Der/Die/Das
    # Capitalize the original word regardless
    capitalized_word = german_word.capitalize()

    return article + capitalized_word, plural 