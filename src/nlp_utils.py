"""
NLP utilities module - redirects to Groq API for all NLP processing.

This module provides a compatibility layer to redirect legacy code to use
the Groq API implementation instead of pattern.de.
"""

from typing import Tuple, List, Dict, Any, Optional
from .groq_generator import get_word_info

def get_german_word_type(word: str) -> str:
    """
    Determine the type of a German word (noun, verb, adjective, etc.)
    
    Args:
        word: The German word to analyze
        
    Returns:
        A string representing the word type
    """
    # Get word info from Groq and extract the word type
    word_info = get_word_info(word)
    return word_info.get('word_type', 'unknown')

def get_plural(word: str) -> Tuple[str, str]:
    """
    Get the plural form of a German noun along with its article
    
    Args:
        word: The German noun to get the plural for
        
    Returns:
        A tuple of (display_with_article, plural_form)
    """
    # Get word info from Groq and extract the required information
    word_info = get_word_info(word)
    
    # Extract gender and plural information
    gender = word_info.get('gender', '')
    plural = word_info.get('plural', '')
    article = ''
    
    # Set the article based on gender
    if gender == 'masculine':
        article = 'der'
    elif gender == 'feminine':
        article = 'die'
    elif gender == 'neuter':
        article = 'das'
    
    # Format the display form with the article
    display = f"{article} {word.capitalize()}" if article else word.capitalize()
    
    # Format the plural (if available)
    plural_form = f"die {plural}" if plural else ""
    
    return display, plural_form

def warmup_parser() -> None:
    """
    Warms up the NLP parser by making a single test API call.
    This ensures that any initialization required by the Groq API is done
    before processing multiple words.
    
    This is a no-op when using Groq since it doesn't need local model warming,
    but it's kept for backward compatibility with the main.py workflow.
    """
    print("Warming up NLP components...")
    # Simply check if get_word_info works by running a test query
    try:
        _ = get_word_info("test")
        print("NLP components ready")
    except Exception as e:
        print(f"Warning: Failed to warm up NLP components: {e}")
        print("This may indicate issues with Groq API connectivity or authentication.")
        print("Check your GROQ_API_KEY environment variable.")
    
# Legacy compatibility functions can be added as needed
# All implementations should call groq_generator functions 