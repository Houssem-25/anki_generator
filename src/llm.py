"""
LLM service for interacting with Groq API.
Handles word processing, rate limiting, and response formatting.
"""

import os
import time
import groq
import re
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

from structures import WordData, WordType, Gender


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, capacity: int = 30, refill_rate: float = 0.5):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill_time = time.time()
    
    def consume(self, tokens: int = 1, block: bool = True) -> bool:
        """Consume tokens from the bucket."""
        self._refill()
        
        if tokens <= self.tokens:
            self.tokens -= tokens
            return True
        
        if not block:
            return False
        
        # Calculate wait time needed
        wait_time = (tokens - self.tokens) / self.refill_rate
        print(f"Rate limit reached. Waiting {wait_time:.2f}s for token refill...")
        time.sleep(wait_time)
        self._refill()
        self.tokens -= tokens
        return True
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.refill_rate
        
        if new_tokens > 0:
            self.tokens = min(self.capacity, self.tokens + new_tokens)
            self.last_refill_time = now


class LLMService(ABC):
    """Abstract base class for LLM services."""
    
    @abstractmethod
    def process_word(self, word: str, target_language: str = "english") -> Optional[WordData]:
        """Process a single word and return structured data."""
        pass
    
    @abstractmethod
    def process_words(self, words: List[str], target_language: str = "english") -> List[WordData]:
        """Process multiple words and return structured data."""
        pass


class GroqLLMService(LLMService):
    """Groq API implementation for LLM service."""
    
    def __init__(self, api_key: str):
        self.client = groq.Client(api_key=api_key)
        self.rate_limiter = RateLimiter()
    
    def process_word(self, word: str, target_language: str = "english") -> Optional[WordData]:
        """Process a single word using Groq API."""
        try:
            # Apply rate limiting
            self.rate_limiter.consume(1, block=True)
            
            # Generate content
            response = self._generate_content(word, target_language)
            if not response:
                return None
            
            # Parse response
            return self._parse_response(word, response)
            
        except Exception as e:
            print(f"Error processing word '{word}': {e}")
            return None
    
    def process_words(self, words: List[str], target_language: str = "english") -> List[WordData]:
        """Process multiple words using Groq API."""
        results = []
        
        for word in words:
            result = self.process_word(word, target_language)
            if result:
                results.append(result)
            else:
                # Add empty result to maintain order
                results.append(self._create_empty_word_data(word))
        
        return results
    
    def _generate_content(self, word: str, target_language: str) -> Optional[str]:
        """Generate content using Groq API."""
        try:
            # Determine word type and create appropriate prompt
            system_content = self._create_system_prompt(word, target_language)
            
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": f"Generate information for the German word: {word}"}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating content for '{word}': {e}")
            return None
    
    def _create_system_prompt(self, word: str, target_language: str) -> str:
        """Create appropriate system prompt based on word characteristics."""
        # Check if the word might be a verb
        is_potential_verb = word.lower().endswith(('en', 'n', 'rn', 'ln')) and len(word) > 2
        
        # Check if the word might be a noun
        is_potential_noun = word.startswith(('der ', 'die ', 'das ', 'Der ', 'Die ', 'Das ')) or (
            len(word) > 0 and word[0].isupper()
        )
        
        if is_potential_verb:
            return self._create_verb_prompt(target_language)
        elif is_potential_noun:
            return self._create_noun_prompt(target_language)
        else:
            return self._create_general_prompt(target_language)
    
    def _create_verb_prompt(self, target_language: str) -> str:
        """Create prompt for verb processing."""
        return f"""You are a German language expert assistant. For the German verb provided, generate:
1. A detailed {target_language} translation of the verb (1-2 phrases maximum explaining the meaning more precisely)
2. An example German sentence using the verb.
3. Ensure the verb is used in its proper form—respecting whether it is trennbar (separable) or nicht trennbar (inseparable)—within the sentence.
4. An accurate {target_language} translation of that sentence
5. The 3rd person singular (er/sie/es) conjugation for Präsens, Perfekt (including auxiliary verb), and Präteritum, separated by commas. Example: er geht, er ist gegangen, er ging
6. Whether the verb requires accusative, dative, or both cases
7. The word type (verb) and any subtypes (regular, separable, reflexive, etc.)
8. Related German words (3-5 words maximum) with their {target_language} translations in parentheses, e.g., "kaufen (to buy), Verkauf (sale), einkaufen (to shop)"
9. Any additional relevant information about usage, nuances, or special considerations

Format your response exactly like this:
Word type: verb, [subtype if applicable]
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
{target_language.capitalize()} translation: <translation>
Conjugation: <er form präsens>, <er form perfekt>, <er form präteritum>
Case: <Akkusativ/Dativ/Both>
Related words: <list of 5 related German words with {target_language} translations in parentheses>
Additional info: <any relevant usage information or nuances>

Keep responses concise and grammatically correct."""
    
    def _create_noun_prompt(self, target_language: str) -> str:
        """Create prompt for noun processing."""
        return f"""You are a German language expert assistant. For the German noun provided, generate:
1. A detailed {target_language} translation of the noun (1-2 phrases maximum explaining the meaning more precisely)
2. An example German sentence using the noun
3. An accurate {target_language} translation of that sentence
4. The gender of the noun (masculine, feminine, neuter)
5. The plural form of the noun
6. The word type (noun)
7. Related German words (3-5 words maximum) with their {target_language} translations in parentheses, e.g., "Buch (book), Buchhandlung (bookstore), Bücherei (library)"
8. Any additional relevant information about usage, nuances, or special considerations

Format your response exactly like this:
Word type: noun
Gender: <masculine/feminine/neuter>
Plural form: <plural>
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
{target_language.capitalize()} translation: <translation>
Related words: <list of 5 related German words with {target_language} translations in parentheses>
Additional info: <any relevant usage information or nuances>

Keep responses concise and grammatically correct."""
    
    def _create_general_prompt(self, target_language: str) -> str:
        """Create prompt for general word processing."""
        return f"""You are a German language expert AI that efficiently analyzes and provides key information about German words. For each given German word, analyze and return the following information in this exact format:

Word type: <adjective/adverb/preposition/etc.>
Word translation: <detailed translation with 1-2 phrases maximum>
German sentence: <sentence>
{target_language.capitalize()} translation: <translation>
Related words: <list of 5 related German words, each with its {target_language} translation in parentheses, e.g., "Buchstabe (letter), Buchstabieren (to spell)">
Additional info: <any relevant grammar information or usage nuances>

Keep responses concise and grammatically correct."""
    
    def _parse_response(self, word: str, response_text: str) -> WordData:
        """Parse the LLM response into structured data."""
        result = self._create_empty_word_data(word)
        
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith("Word type:"):
                result.word_type = self._parse_word_type(line.replace("Word type:", "").strip())
            elif line.startswith("Word translation:"):
                result.word_translation = line.replace("Word translation:", "").strip()
            elif line.startswith("German sentence:"):
                result.phrase = line.replace("German sentence:", "").strip()
            elif line.startswith("English translation:") or line.startswith("Translation:"):
                result.translation = line.split(":", 1)[1].strip()
            elif line.startswith("Conjugation:"):
                result.conjugation = line.replace("Conjugation:", "").strip()
            elif line.startswith("Case:"):
                result.case_info = line.replace("Case:", "").strip()
            elif line.startswith("Gender:"):
                result.gender = self._parse_gender(line.replace("Gender:", "").strip())
            elif line.startswith("Plural form:"):
                result.plural = line.replace("Plural form:", "").strip()
            elif line.startswith("Additional info:"):
                result.additional_info = line.replace("Additional info:", "").strip()
            elif line.startswith("Related words:"):
                result.related_words = line.replace("Related words:", "").strip()
        
        return result
    
    def _create_empty_word_data(self, word: str) -> WordData:
        """Create empty word data structure."""
        return WordData(
            word=word,
            word_translation="",
            phrase="",
            translation="",
            word_type=WordType.OTHER,
            conjugation="",
            case_info="",
            gender=None,
            plural="",
            additional_info="",
            related_words=""
        )
    
    def _parse_word_type(self, word_type_str: str) -> WordType:
        """Parse word type string to enum."""
        word_type_str = word_type_str.lower()
        
        if "noun" in word_type_str:
            return WordType.NOUN
        elif "verb" in word_type_str:
            return WordType.VERB
        elif "adjective" in word_type_str:
            return WordType.ADJECTIVE
        elif "adverb" in word_type_str:
            return WordType.ADVERB
        elif "preposition" in word_type_str:
            return WordType.PREPOSITION
        else:
            return WordType.OTHER
    
    def _parse_gender(self, gender_str: str) -> Optional[Gender]:
        """Parse gender string to enum."""
        gender_str = gender_str.lower()
        
        if "masculine" in gender_str:
            return Gender.MASCULINE
        elif "feminine" in gender_str:
            return Gender.FEMININE
        elif "neuter" in gender_str:
            return Gender.NEUTER
        else:
            return None


def create_llm_service(api_key: str) -> LLMService:
    """Factory function to create LLM service."""
    return GroqLLMService(api_key)
