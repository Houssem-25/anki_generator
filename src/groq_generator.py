import os
import groq
from typing import List, Dict, Tuple
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
    - German word
    - Example German phrase
    - English translation of the phrase
    
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
            response = client.chat.completions.create(
                model="llama3-8b-8192",  # Using Llama 3 model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a German language expert assistant. For each German word provided, generate:"
                                  "1. An example German sentence using the word"
                                  "2. An accurate English translation of that sentence"
                                  "Format your response exactly like this example:"
                                  "German sentence: <sentence>"
                                  "English translation: <translation>"
                    },
                    {
                        "role": "user",
                        "content": f"Generate an example sentence and translation for the German word: {word}"
                    }
                ],
                temperature=0.3,
                max_tokens=256,
            )
            
            # Process the response
            result = process_groq_response(word, response.choices[0].message.content)
            results.append(result)
            
        except Exception as e:
            print(f"Error processing word '{word}' with Groq API: {e}")
            # Add empty result to maintain word order
            results.append({
                "word": word,
                "phrase": "",
                "translation": ""
            })
            
    return results

def process_groq_response(word: str, response_text: str) -> Dict:
    """
    Process the response from Groq API to extract the German sentence and English translation.
    
    Args:
        word: The original German word
        response_text: The response text from Groq API
        
    Returns:
        Dictionary with word, German phrase, and English translation
    """
    result = {
        "word": word,
        "phrase": "",
        "translation": ""
    }
    
    lines = response_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if line.startswith("German sentence:"):
            result["phrase"] = line.replace("German sentence:", "").strip()
        elif line.startswith("English translation:"):
            result["translation"] = line.replace("English translation:", "").strip()
    
    return result

def format_for_anki_import(processed_words: List[Dict]) -> List[str]:
    """
    Format the processed words for Anki import.
    
    Args:
        processed_words: List of dictionaries with word, phrase, and translation
        
    Returns:
        List of strings in the format "word; phrase; translation"
    """
    formatted_lines = []
    
    for item in processed_words:
        formatted_line = f"{item['word']}; {item['phrase']}; {item['translation']}"
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
        with open(input_file_path, 'r', encoding='utf-8') as infile:
            words = [line.strip() for line in infile.readlines() if line.strip()]
            
        print(f"Processing {len(words)} words with Groq API...")
        processed_data = process_german_words(words)
        formatted_lines = format_for_anki_import(processed_data)
        
        if output_file_path:
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