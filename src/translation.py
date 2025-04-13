from deep_translator import GoogleTranslator
from . import config

def translate_to_english(german_word):
    """Translates a German word to English using Google Translator."""
    try:
        # Initialize translator within the function to potentially handle 
        # different source/target languages if config changes.
        translator = GoogleTranslator(source=config.SOURCE_LANG, target=config.TARGET_LANG)
        english_translation = translator.translate(german_word)
        return english_translation
    except Exception as e:
        print(f"Error translating '{german_word}': {e}")
        return None # Return None or raise an exception to indicate failure 