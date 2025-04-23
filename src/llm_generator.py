import os
import groq
from typing import List, Dict, Tuple, Union
from pathlib import Path
# from tqdm import tqdm # Removed
from . import config

# Initialize the Groq client with the API key from environment variable
client = None
try:
    client = groq.Client(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    print(f"Failed to initialize Groq client: {e}")
    print("Make sure to set GROQ_API_KEY environment variable.")

def process_german_words(words: List[str]) -> List[Dict]:
    """
    Process a list of German words using Groq API to generate:
    - German word with article (for nouns)
    - English meaning of the word
    - Example German phrase
    - English translation of the phrase
    - For verbs: conjugation and case information
    - For nouns: plural form and gender
    - Word type detection (noun, verb, adjective, etc.)
    
    Args:
        words: List of German words to process
        
    Returns:
        List of dictionaries containing the processed information
    """
    if not client:
        print("Groq client not initialized. Check your API key.")
        return []
        
    results = []
    
    # Loop through words (removed tqdm wrapper as it's now called per word)
    for word in words:
        try:
            # First check if the word might be a verb (ends with 'en' or 'n' typically)
            is_potential_verb = word.lower().endswith(('en', 'n', 'rn', 'ln')) and len(word) > 2
            # Check if the word might be a noun (starts with article or capitalized)
            is_potential_noun = word.startswith(('der ', 'die ', 'das ', 'Der ', 'Die ', 'Das ')) or (len(word) > 0 and word[0].isupper())
            
            # Create the appropriate prompt based on word type
            if is_potential_verb:
                system_content = """You are a German language expert assistant. For the German verb provided, generate:
1. A detailed English translation of the verb (1-2 phrases maximum explaining the meaning more precisely)
2. An example German sentence using the verb.
3. Ensure the verb is used in its proper form—respecting whether it is trennbar (separable) or nicht trennbar (inseparable)—within the sentence.
4. An accurate English translation of that sentence
5. The 3rd person singular (er/sie/es) conjugation for Präsens, Perfekt (including auxiliary verb), and Präteritum, separated by commas. Example: er geht, er ist gegangen, er ging
6. Whether the verb requires accusative, dative, or both cases
7. The word type (verb) and any subtypes (regular, separable, reflexive, etc.)
8. Related German words (3-5 words maximum) with their English translations in parentheses, e.g., "kaufen (to buy), Verkauf (sale), einkaufen (to shop)"
9. Any additional relevant information about usage, nuances, or special considerations

Format your response exactly like this:
Word type: verb, [subtype if applicable]
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
English translation: <translation>
Conjugation: <er form präsens>, <er form perfekt>, <er form präteritum>
Case: <Akkusativ/Dativ/Both>
Related words: <list of 5 related German words with English translations in parentheses>
Additional info: <any relevant usage information or nuances>

Keep responses concise and grammatically correct."""
            elif is_potential_noun:
                system_content = """You are a German language expert assistant. For the German noun provided, generate:
1. A detailed English translation of the noun (1-2 phrases maximum explaining the meaning more precisely)
2. An example German sentence using the noun
3. An accurate English translation of that sentence
4. The gender of the noun (masculine, feminine, neuter)
5. The plural form of the noun
6. The word type (noun)
7. Related German words (3-5 words maximum) with their English translations in parentheses, e.g., "Buch (book), Buchhandlung (bookstore), Bücherei (library)"
8. Any additional relevant information about usage, nuances, or special considerations

Format your response exactly like this:
Word type: noun
Gender: <masculine/feminine/neuter>
Plural form: <plural>
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
English translation: <translation>
Related words: <list of 5 related German words with English translations in parentheses>
Additional info: <any relevant usage information or nuances>

Keep responses concise and grammatically correct."""
            else:
                system_content = """You are a German language expert AI that efficiently analyzes and provides key information about German words. For each given German word, analyze and return the following information in this exact format:

Word type: <adjective/adverb/preposition/etc.>
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
English translation: <translation>
Related words: <list of 5 related German words, each with its English translation in parentheses, e.g., "Buchstabe (letter), Buchstabieren (to spell)">
Additional info: <any relevant grammar information or usage nuances>

Keep responses concise and grammatically correct."""
            
            response = client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",  # meta-llama/llama-4-maverick-17b-128e-instruct
                messages=[
                    {
                        "role": "system",
                        "content": system_content
                    },
                    {
                        "role": "user",
                        "content": f"Generate information for the German word: {word}"
                    }
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            # Debug: Print the full LLM response if debug mode is enabled
            if hasattr(config, 'DEBUG') and config.DEBUG:
                print("\n=== DEBUG: FULL LLM RESPONSE ===")
                print(f"Word: {word}")
                print(response.choices[0].message.content)
                print("=== END DEBUG OUTPUT ===\n")
            
            # Process the response
            result = process_groq_response(word, response.choices[0].message.content)
            results.append(result)
            
        except Exception as e:
            print(f"Error processing word '{word}' with Groq API: {e}")
            # Add empty result to maintain word order
            results.append({
                "word": word,
                "word_translation": "",
                "phrase": "",
                "translation": "",
                "word_type": "",
                "conjugation": "",
                "case_info": "",
                "gender": "",
                "plural": "",
                "additional_info": "",
                "related_words": ""
            })
            
    return results

def process_groq_response(word: str, response_text: str) -> Dict:
    """
    Process the response from Groq API to extract information.
    
    Args:
        word: The original German word
        response_text: The response text from Groq API
        
    Returns:
        Dictionary with all linguistic information about the word
    """
    result = {
        "word": word,
        "word_translation": "",
        "phrase": "",
        "translation": "",
        "word_type": "",
        "conjugation": "",
        "case_info": "",
        "gender": "",
        "plural": "",
        "additional_info": "",
        "related_words": ""
    }
    
    lines = response_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith("Word type:"):
            result["word_type"] = line.replace("Word type:", "").strip()
        elif line.startswith("Word translation:"):
            result["word_translation"] = line.replace("Word translation:", "").strip()
        elif line.startswith("German sentence:"):
            result["phrase"] = line.replace("German sentence:", "").strip()
        elif line.startswith("English translation:"):
            result["translation"] = line.replace("English translation:", "").strip()
        elif line.startswith("Conjugation:"):
            result["conjugation"] = line.replace("Conjugation:", "").strip()
        elif line.startswith("Case:"):
            result["case_info"] = line.replace("Case:", "").strip()
        elif line.startswith("Gender:"):
            result["gender"] = line.replace("Gender:", "").strip()
        elif line.startswith("Plural form:"):
            result["plural"] = line.replace("Plural form:", "").strip()
        elif line.startswith("Additional info:"):
            result["additional_info"] = line.replace("Additional info:", "").strip()
        elif line.startswith("Related words:"):
            result["related_words"] = line.replace("Related words:", "").strip()
    
    return result

def format_for_anki_import(processed_words: List[Dict]) -> List[str]:
    """
    Format the processed words for Anki import.
    
    Args:
        processed_words: List of dictionaries with word and related information
        
    Returns:
        List of strings in a format ready for the main application
    """
    formatted_lines = []
    
    # HTML color spans for articles
    article_html = {
        "masculine": '<span style="color: rgb(10, 2, 255)">Der</span> ',
        "feminine": '<span style="color: rgb(170, 0, 0)">Die</span> ',
        "neuter": '<span style="color: rgb(0, 255, 51)">Das</span> ',
    }
    
    for item in processed_words:
        word_type = item.get('word_type', '').lower()
        word = item['word']
        translation = item.get('word_translation', '')
        example_de = item.get('phrase', '')
        example_en = item.get('translation', '')
        conjugation = item.get('conjugation', '')
        case_info = item.get('case_info', '')
        gender = item.get('gender', '').lower()
        plural = item.get('plural', '')
        additional_info = item.get('additional_info', '')
        related_words = item.get('related_words', '')

        # --- English Part (Front of Card) ---
        english_part = translation
        if example_en:
            # Use <br><br> for spacing on the front
            english_part += f"<br><br>{example_en}"
        
        # --- German Part (Back of Card) ---
        german_parts_list = [] # Build the German part step-by-step
        core_german_info = ""

        if "noun" in word_type:
            article_span = article_html.get(gender, '')
            # Ensure proper spacing if article exists
            word_display = f"{article_span}{word}" if article_span else word
            plural_display = f"({plural})" if plural else ""
            # Add space only if both word and plural exist
            core_german_info = f"{word_display} {plural_display}".strip()
            
        elif "verb" in word_type:
            core_german_info = word # Start with the verb infinitive
            if conjugation:
                 core_german_info += f"<br><br><br>Conj: {conjugation}" # Add conj with spacing
            if case_info:
                 core_german_info += f"<br><br><br>Case: {case_info}" # Add case right after
                 
        else: # Adjectives, Adverbs, Prepositions, etc.
             core_german_info = word # Just the word itself

        # Add the core info first
        if core_german_info:
            german_parts_list.append(core_german_info)

        # Add example sentence if it exists
        if example_de:
             german_parts_list.append(example_de)

        # Prepare related words section
        related_part = ""
        if related_words:
            related_part = f"Related: {related_words}"
            german_parts_list.append(related_part)

        # Prepare additional info section
        info_part = ""
        if additional_info:
            info_part = f"Info: {additional_info}"
            german_parts_list.append(info_part)
            
        # Join the German parts with the desired separator
        german_part_final = "<br><br><br>".join(p for p in german_parts_list if p) # Use 3 breaks, filter empty

        # Combine English and German parts for the final Anki line
        final_line = f"{english_part};{german_part_final}"
        formatted_lines.append(final_line)
        
    return formatted_lines 