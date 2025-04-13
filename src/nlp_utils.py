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
        # The german_nouns library uses dictionary-like access but doesn't have .get()
        try:
            # Directly access the noun data using dictionary syntax
            noun_entries = nouns[german_word]
            # Check if we found entries
            has_entries = len(noun_entries) > 0
            print(f"Noun check for '{german_word}': Found in dictionary, Entries: {len(noun_entries)}")
            if has_entries:
                return "noun"
        except KeyError:
            # Word is not in the nouns dictionary
            print(f"Noun check for '{german_word}': Not found in dictionary")
    except Exception as e:
        print(f"Error determining word type for '{german_word}': {e}")
    return "unknown"

def get_plural(german_word):
    """Gets the article and plural form for a German noun."""
    plural = ""
    article = ""
    
    try:
        # Try to get noun entries using dictionary-like access
        word_data_list = nouns[german_word]
        
        if not word_data_list or len(word_data_list) == 0:
            print(f"Warning: No data found for noun '{german_word}' in german-nouns library.")
            # Return the word capitalized as a fallback
            return german_word.capitalize(), ""
            
        # Use the first entry if multiple exist
        word_data = word_data_list[0]  
        flexion = word_data.get("flexion", {})
        genus_keys = [k for k in word_data if k.startswith("genus")]
        
        # --- Get Article ---
        if "genus" in word_data:
            article = config.GENDER_TO_ARTICLE_HTML.get(word_data["genus"], "")
        elif genus_keys:  # Handle cases like 'genus 1', 'genus 2'
            articles = [config.GENDER_TO_ARTICLE_HTML.get(word_data[g], "") for g in sorted(genus_keys)]
            article = " ".join(filter(None, articles))
        
        # Capitalize the original word
        capitalized_word = german_word.capitalize()
        
        # --- Get Plural Form ---
        plural_form = ""
        if "nominativ plural" in flexion:
            plural_form = flexion["nominativ plural"]
        elif "nominativ plural 2" in flexion:
            plural_form = flexion["nominativ plural 2"]
        
        # Format the plural with colored article if we have a plural form
        if plural_form:
            # Add two spaces after <br> for consistent formatting with expected output
            plural = f"<br> {config.GENDER_TO_ARTICLE_HTML.get('pl', '')}{plural_form}"
        
        return article + capitalized_word, plural
        
    except KeyError:
        print(f"Warning: '{german_word}' not found in german-nouns library.")
        return german_word.capitalize(), ""
    except Exception as e:
        print(f"Error getting plural for '{german_word}': {e}")
        return german_word.capitalize(), "" 