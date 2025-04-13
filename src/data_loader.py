import pickle
from . import config

def load_pickle_data():
    """Loads the German-to-English translation data from pickle files."""
    try:
        with open(config.GERMAN_TO_ENG_PICKLE, 'rb') as handle:
            german_to_eng = pickle.load(handle)
    except FileNotFoundError:
        print(f"Error: File not found at {config.GERMAN_TO_ENG_PICKLE}")
        german_to_eng = []
    except Exception as e:
        print(f"Error loading {config.GERMAN_TO_ENG_PICKLE}: {e}")
        german_to_eng = []

    try:
        with open(config.GERMAN_TO_ENG_IDS_PICKLE, 'rb') as handle:
            german_to_eng_ids = pickle.load(handle)
    except FileNotFoundError:
        print(f"Error: File not found at {config.GERMAN_TO_ENG_IDS_PICKLE}")
        german_to_eng_ids = []
    except Exception as e:
        print(f"Error loading {config.GERMAN_TO_ENG_IDS_PICKLE}: {e}")
        german_to_eng_ids = []

    try:
        with open(config.NEW_ENGLISH_TEXTS_PICKLE, 'rb') as handle:
            new_english_texts = pickle.load(handle)
    except FileNotFoundError:
        print(f"Error: File not found at {config.NEW_ENGLISH_TEXTS_PICKLE}")
        new_english_texts = []
    except Exception as e:
        print(f"Error loading {config.NEW_ENGLISH_TEXTS_PICKLE}: {e}")
        new_english_texts = []

    return german_to_eng, german_to_eng_ids, new_english_texts 