import os
import groq
from typing import List, Dict, Tuple, Union
from pathlib import Path
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
2. An example German sentence using the verb
3. An accurate English translation of that sentence
4. Conjugation of the verb in 3rd person singular (er) for Präsens, Perfekt, and Präteritum only
5. Whether the verb requires accusative, dative, or both cases
6. The word type (verb) and any subtypes (regular, separable, reflexive, etc.)

Format your response exactly like this:
Word type: verb, [subtype if applicable]
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
English translation: <translation>
Conjugation: Präsens: er <form>, Perfekt: er <form>, Präteritum: er <form>
Case: <Akkusativ/Dativ/Both>

Keep responses concise and grammatically correct."""
            elif is_potential_noun:
                system_content = """You are a German language expert assistant. For the German noun provided, generate:
1. A detailed English translation of the noun (1-2 phrases maximum explaining the meaning more precisely)
2. An example German sentence using the noun
3. An accurate English translation of that sentence
4. The gender of the noun (masculine, feminine, neuter)
5. The plural form of the noun
6. The word type (noun)

Format your response exactly like this:
Word type: noun
Gender: <masculine/feminine/neuter>
Plural form: <plural>
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
English translation: <translation>

Keep responses concise and grammatically correct."""
            else:
                system_content = """You are a German language expert assistant. For the German word provided, generate:
1. The word type (adjective, adverb, preposition, etc.)
2. A detailed English translation of the word (1-2 phrases maximum explaining the meaning more precisely)
3. An example German sentence using the word
4. An accurate English translation of that sentence
5. Any additional relevant grammatical information

Format your response exactly like this:
Word type: <adjective/adverb/preposition/etc.>
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
English translation: <translation>
Additional info: <any relevant grammar information>

Keep responses concise and grammatically correct."""
            
            response = client.chat.completions.create(
                model="llama3-8b-8192",  # Using Llama 3 model
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
                "additional_info": ""
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
        "additional_info": ""
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
    
    return result

def get_word_info(word: str) -> Dict[str, str]:
    """
    Get detailed information about a German word using Groq API.
    This function is used by nlp_utils.py as a compatibility layer.
    
    Args:
        word: The German word to analyze
        
    Returns:
        Dictionary containing word information (word_type, gender, plural, etc.)
    """
    # Process a single word with Groq
    processed_data = process_german_words([word])
    
    # Return the word info if available, otherwise return empty dict
    if processed_data and len(processed_data) > 0:
        return processed_data[0]
    else:
        return {
            "word": word,
            "word_translation": "",
            "phrase": "",
            "translation": "",
            "word_type": "unknown",
            "conjugation": "",
            "case_info": "",
            "gender": "",
            "plural": "",
            "additional_info": ""
        }

def format_for_anki_import(processed_words: List[Dict]) -> List[str]:
    """
    Format the processed words for Anki import.
    
    Args:
        processed_words: List of dictionaries with word and related information
        
    Returns:
        List of strings in a format ready for anki_generator.py
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
        example = item.get('phrase', '')
        example_translation = item.get('translation', '')
        
        # GERMAN PART (second part after the semicolon)
        # ----------
        # For nouns: include colored article, word, and plural
        if 'noun' in word_type:
            # Clean up word from existing articles if present
            clean_word = word
            for article_pattern in ["der ", "die ", "das ", "Der ", "Die ", "Das "]:
                if clean_word.startswith(article_pattern):
                    clean_word = clean_word[len(article_pattern):]
            
            # Add colored article based on gender
            gender = item.get('gender', '').lower()
            if 'masculine' in gender:
                article_colored = article_html["masculine"]
            elif 'feminine' in gender:
                article_colored = article_html["feminine"]
            elif 'neuter' in gender:
                article_colored = article_html["neuter"]
            else:
                article_colored = ""
            
            # Format plural if available
            plural = item.get('plural', '')
            if plural:
                plural_info = f" ({plural})"
            else:
                plural_info = ""
                
            # Build German part with word and plural
            german_part = f"{article_colored}{clean_word}{plural_info}"
            
            # Include example after word/plural info
            if example:
                german_part = f"{german_part}<br>{example}"
            
        # For verbs: include word, conjugation and case
        elif 'verb' in word_type:
            # Get conjugation and case if available
            conjugation = item.get('conjugation', '')
            case_info = item.get('case_info', '')
            
            # Remove example from case info (to avoid duplication)
            if " - Example:" in case_info:
                case_info = case_info.split(" - Example:")[0].strip()
            
            # Build German part with word and grammatical details
            german_part = f"{word}<br>Conjugation: {conjugation}<br>Case: {case_info}"
            
            # Include example after grammatical info
            if example:
                german_part = f"{german_part}<br>{example}"
            
        # For other word types: just include the word and any additional info
        else:
            additional = item.get('additional_info', '')
            
            # Build German part with word
            german_part = f"{word}"
            
            # Add additional info if available
            if additional:
                german_part = f"{german_part}<br>Info: {additional}"
            
            # Include example after additional info
            if example:
                german_part = f"{german_part}<br>{example}"
        
        # ENGLISH PART (first part before the semicolon)
        # -----------
        # Include translation and example sentence translation
        english_part = translation
        
        # Add example translation directly without "Example:" prefix
        if example_translation:
            english_part = f"{english_part}<br>{example_translation}"
        
        # Combine parts in the new order: ENGLISH; GERMAN
        formatted_line = f"{english_part};{german_part}"
        formatted_lines.append(formatted_line)
    
    return formatted_lines

def process_words_file(input_file_path=config.INPUT_WORDS_FILE, 
                      output_file_path=None) -> Tuple[List[str], List[Dict]]:
    """
    Process a file containing German words using Groq API.
    
    Args:
        input_file_path: Path to the input file with German words
        output_file_path: Optional path to save the formatted output
        
    Returns:
        Tuple of (formatted lines for Anki import, raw processed data)
    """
    try:
        # Convert to Path objects if they're strings
        input_file_path = Path(input_file_path)
        if output_file_path:
            output_file_path = Path(output_file_path)
        
        # Ensure input directory exists
        if not input_file_path.exists():
            print(f"Error: Input file not found at {input_file_path}")
            return [], []
        
        # Read words from the input file
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            words = [line.strip() for line in infile.readlines() if line.strip()]
            
        print(f"Processing {len(words)} words with Groq API...")
        processed_data = process_german_words(words)
        formatted_lines = format_for_anki_import(processed_data)
        
        if output_file_path:
            # Ensure output directory exists
            os.makedirs(output_file_path.parent, exist_ok=True)
            
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                for line in formatted_lines:
                    outfile.write(line + '\n')
            print(f"Saved formatted output to {output_file_path}")
            
        return formatted_lines, processed_data
        
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file_path}")
        return [], []
    except Exception as e:
        print(f"Error processing words file: {e}")
        return [], [] 