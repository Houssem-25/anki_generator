import pytest
import os
import csv
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call
from typing import List, Dict, Tuple

# Adjust the path to import from the 'src' directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the module under test and config
from src import llm_generator
from src import config
import groq # Import groq for APIError

# --- Fixtures ---

@pytest.fixture
def sample_words() -> List[str]:
    return ["Haus", "laufen", "schnell"]

@pytest.fixture
def mock_groq_client():
    """Fixture to mock the Groq client and its chat completion method."""
    with patch('src.llm_generator.client', autospec=True) as mock_client:
        # Mock the chat.completions.create method
        mock_response = MagicMock()
        # We will set the response content per test
        # mock_response.choices[0].message.content = "Default mock response"
        mock_client.chat.completions.create.return_value = mock_response
        yield mock_client

@pytest.fixture
def mock_input_file(tmp_path, sample_words):
    """Creates a temporary input file with sample words."""
    input_path = tmp_path / "input_words.txt"
    with open(input_path, 'w') as f:
        for word in sample_words:
            f.write(word + '\n')
    return input_path

# --- Tests for process_groq_response ---

def test_process_groq_response_full_noun():
    word = "Haus"
    response_text = """
    Word type: noun
    Gender: neuter
    Plural form: Häuser
    Word translation: house, building
    German sentence: Das ist mein Haus.
    English translation: This is my house.
    Related words: Gebäude (building), Wohnung (apartment), Zuhause (home)
    Additional info: Common noun.
    """
    expected_result = {
        "word": "Haus",
        "word_translation": "house, building",
        "phrase": "Das ist mein Haus.",
        "translation": "This is my house.",
        "word_type": "noun",
        "conjugation": "",
        "case_info": "",
        "gender": "neuter",
        "plural": "Häuser",
        "additional_info": "Common noun.",
        "related_words": "Gebäude (building), Wohnung (apartment), Zuhause (home)"
    }
    assert llm_generator.process_groq_response(word, response_text) == expected_result

def test_process_groq_response_full_verb():
    word = "laufen"
    response_text = """
    Word type: verb, irregular
    Word translation: to run, to walk
    German sentence: Ich laufe jeden Tag.
    English translation: I run every day.
    Conjugation: Präsens: er läuft, Perfekt: er ist gelaufen, Präteritum: er lief
    Case: Akkusativ
    Related words: Rennen (to race), Spaziergang (walk), Lauf (run)
    Additional info: Can also mean 'to walk'.
    """
    expected_result = {
        "word": "laufen",
        "word_translation": "to run, to walk",
        "phrase": "Ich laufe jeden Tag.",
        "translation": "I run every day.",
        "word_type": "verb, irregular",
        "conjugation": "Präsens: er läuft, Perfekt: er ist gelaufen, Präteritum: er lief",
        "case_info": "Akkusativ",
        "gender": "",
        "plural": "",
        "additional_info": "Can also mean 'to walk'.",
        "related_words": "Rennen (to race), Spaziergang (walk), Lauf (run)"
    }
    assert llm_generator.process_groq_response(word, response_text) == expected_result

def test_process_groq_response_other_type():
    word = "schnell"
    response_text = """
    Word type: adjective
    Word translation: fast, quick
    German sentence: Das Auto ist schnell.
    English translation: The car is fast.
    Related words: Geschwindigkeit (speed), rasch (swift)
    Additional info: Basic adjective.
    """
    expected_result = {
        "word": "schnell",
        "word_translation": "fast, quick",
        "phrase": "Das Auto ist schnell.",
        "translation": "The car is fast.",
        "word_type": "adjective",
        "conjugation": "",
        "case_info": "",
        "gender": "",
        "plural": "",
        "additional_info": "Basic adjective.",
        "related_words": "Geschwindigkeit (speed), rasch (swift)"
    }
    assert llm_generator.process_groq_response(word, response_text) == expected_result

def test_process_groq_response_missing_fields():
    word = "Test"
    response_text = """
    Word type: test_type
    Word translation: test_translation
    """ # Missing many fields
    expected_result = {
        "word": "Test",
        "word_translation": "test_translation",
        "phrase": "",
        "translation": "",
        "word_type": "test_type",
        "conjugation": "",
        "case_info": "",
        "gender": "",
        "plural": "",
        "additional_info": "",
        "related_words": ""
    }
    assert llm_generator.process_groq_response(word, response_text) == expected_result

def test_process_groq_response_empty_response():
    word = "Empty"
    response_text = ""
    expected_result = {
        "word": "Empty",
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
    assert llm_generator.process_groq_response(word, response_text) == expected_result

# --- Tests for format_for_anki_import ---

def test_format_for_anki_import_noun():
    processed_words = [{
        "word": "Haus",
        "word_translation": "house",
        "phrase": "Das ist mein Haus.",
        "translation": "This is my house.",
        "word_type": "noun",
        "gender": "neuter",
        "plural": "Häuser",
        "related_words": "Gebäude, Wohnung",
        "additional_info": "Common noun"
    }]
    expected_format = [
        "house<br>This is my house.;<span style=\"color: rgb(0, 255, 51)\">Das</span> Haus (Häuser)<br>Das ist mein Haus.<br>Related: Gebäude, Wohnung<br>Info: Common noun"
    ]
    assert llm_generator.format_for_anki_import(processed_words) == expected_format

def test_format_for_anki_import_verb():
    processed_words = [{
        "word": "laufen",
        "word_translation": "to run, to walk",
        "phrase": "Ich laufe jeden Tag.",
        "translation": "I run every day.",
        "word_type": "verb, irregular",
        "conjugation": "Präsens: er läuft, Perfekt: er ist gelaufen, Präteritum: er lief",
        "case_info": "Akkusativ",
        "related_words": "Rennen, Spaziergang",
        "additional_info": "Can mean walk"
    }]
    expected_format = [
        "to run, to walk<br>I run every day.;laufen<br>Präsens: er läuft, Perfekt: er ist gelaufen, Präteritum: er lief<br>Case: Akkusativ<br>Ich laufe jeden Tag.<br>Related: Rennen, Spaziergang<br>Info: Can mean walk"
    ]
    assert llm_generator.format_for_anki_import(processed_words) == expected_format

def test_format_for_anki_import_other():
    processed_words = [{
        "word": "schnell",
        "word_translation": "fast, quick",
        "phrase": "Das Auto ist schnell.",
        "translation": "The car is fast.",
        "word_type": "adjective",
        "related_words": "Geschwindigkeit, rasch",
        "additional_info": "Basic adjective"
    }]
    expected_format = [
        "fast, quick<br>The car is fast.;schnell<br>Das Auto ist schnell.<br>Related: Geschwindigkeit, rasch<br>Info: Basic adjective"
    ]
    assert llm_generator.format_for_anki_import(processed_words) == expected_format

def test_format_for_anki_import_missing_fields():
    processed_words = [{
        "word": "Test",
        "word_translation": "test",
        "word_type": "noun", # Missing gender, plural etc.
        "phrase": "Ein Test.",
        "translation": "A test."
    }]
    # Should handle missing fields gracefully
    expected_format = [
        "test<br>A test.;Test<br>Ein Test."
    ]
    assert llm_generator.format_for_anki_import(processed_words) == expected_format

def test_format_for_anki_import_multiple_words():
    processed_words = [
        {
            "word": "Haus", "word_type": "noun", "gender": "neuter", "plural": "Häuser",
            "word_translation": "house", "phrase": "Das Haus", "translation": "The house"
        },
        {
            "word": "laufen", "word_type": "verb", "conjugation": "er läuft",
            "word_translation": "to run", "phrase": "Ich laufe", "translation": "I run"
        }
    ]
    expected_format = [
        "house<br>The house;<span style=\"color: rgb(0, 255, 51)\">Das</span> Haus (Häuser)<br>Das Haus",
        "to run<br>I run;laufen<br>er läuft<br>Ich laufe"
    ]
    assert llm_generator.format_for_anki_import(processed_words) == expected_format

# --- Tests for process_german_words ---

@patch('src.llm_generator.process_groq_response')
def test_process_german_words_success(mock_process_response, mock_groq_client, sample_words):
    """Test successful processing of multiple words."""
    # Define mock responses from Groq for each word
    mock_groq_responses = {
        "Haus": "Word type: noun\nGender: neuter\nPlural form: Häuser\nWord translation: house",
        "laufen": "Word type: verb\nWord translation: to run\nConjugation: er läuft",
        "schnell": "Word type: adjective\nWord translation: fast"
    }
    # Define expected outputs from process_groq_response for each word
    mock_processed_data = {
        "Haus": {"word": "Haus", "word_type": "noun", "gender": "neuter", "plural": "Häuser", "word_translation": "house"},
        "laufen": {"word": "laufen", "word_type": "verb", "conjugation": "er läuft", "word_translation": "to run"},
        "schnell": {"word": "schnell", "word_type": "adjective", "word_translation": "fast"}
    }

    # Configure the mock Groq client to return specific responses based on user content
    def side_effect(*args, **kwargs):
        messages = kwargs.get('messages', [])
        user_content = next((m['content'] for m in messages if m['role'] == 'user'), None)
        mock_resp = MagicMock()
        if user_content:
            word = user_content.split(': ')[-1]
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = mock_groq_responses.get(word, "Error: Word not mocked")
            return mock_resp
        raise ValueError("No user content found in messages")

    mock_groq_client.chat.completions.create.side_effect = side_effect

    # Configure the mock process_groq_response
    mock_process_response.side_effect = lambda w, r: mock_processed_data.get(w, {})

    results = llm_generator.process_german_words(sample_words)

    assert len(results) == len(sample_words)
    assert mock_groq_client.chat.completions.create.call_count == len(sample_words)
    assert mock_process_response.call_count == len(sample_words)

    # Check that the correct processed data was returned
    assert results[0] == mock_processed_data["Haus"]
    assert results[1] == mock_processed_data["laufen"]
    assert results[2] == mock_processed_data["schnell"]

    # Check system prompts were selected correctly (simplified check based on word type)
    calls = mock_groq_client.chat.completions.create.call_args_list
    assert "noun" in calls[0].kwargs['messages'][0]['content'] # Haus -> noun prompt
    assert "verb" in calls[1].kwargs['messages'][0]['content'] # laufen -> verb prompt
    assert "adjective/adverb/preposition" in calls[2].kwargs['messages'][0]['content'] # schnell -> other prompt

@patch('src.llm_generator.process_groq_response')
def test_process_german_words_api_error(mock_process_response, mock_groq_client, sample_words, capsys):
    """Test handling of Groq API errors."""
    error_word = "laufen"
    api_error_message = "API rate limit exceeded"

    # Configure the mock Groq client to raise an error for one word
    def side_effect(*args, **kwargs):
        messages = kwargs.get('messages', [])
        user_content = next((m['content'] for m in messages if m['role'] == 'user'), None)
        mock_resp = MagicMock()
        if user_content:
            word = user_content.split(': ')[-1]
            if word == error_word:
                # Raise a standard Exception instead of specific groq.APIError
                raise Exception(api_error_message)
            mock_resp.choices = [MagicMock()]
            mock_resp.choices[0].message.content = f"Word type: test\nWord translation: test_{word}"
            return mock_resp
        raise ValueError("No user content found in messages")

    mock_groq_client.chat.completions.create.side_effect = side_effect

    # Mock process_groq_response for the successful calls
    mock_process_response.side_effect = lambda w, r: {"word": w, "word_type": "test", "word_translation": f"test_{w}"} if w != error_word else None

    results = llm_generator.process_german_words(sample_words)

    assert len(results) == len(sample_words)
    assert mock_groq_client.chat.completions.create.call_count == len(sample_words)
    # process_groq_response only called for successful API calls
    assert mock_process_response.call_count == len(sample_words) - 1

    # Check the successful results
    assert results[0]['word_translation'] == "test_Haus"
    assert results[2]['word_translation'] == "test_schnell"

    # Check the result for the failed word
    failed_result = results[1]
    assert failed_result['word'] == error_word
    assert failed_result['word_translation'] == ""
    assert failed_result['word_type'] == ""

    # Check error message printed
    captured = capsys.readouterr()
    assert f"Error processing word '{error_word}' with Groq API: {api_error_message}" in captured.out

def test_process_german_words_no_client(sample_words, capsys):
    """Test behavior when Groq client is not initialized."""
    with patch('src.llm_generator.client', None):
        results = llm_generator.process_german_words(sample_words)
        assert results == []
        captured = capsys.readouterr()
        assert "Groq client not initialized" in captured.out

# --- Tests for get_word_info ---

@patch('src.llm_generator.process_german_words')
def test_get_word_info_success(mock_process_german_words):
    """Test successful retrieval of word info."""
    word = "Einzelwort"
    expected_info = {"word": word, "word_type": "noun", "gender": "neuter"}
    mock_process_german_words.return_value = [expected_info]

    result = llm_generator.get_word_info(word)

    mock_process_german_words.assert_called_once_with([word])
    assert result == expected_info

@patch('src.llm_generator.process_german_words', return_value=[])
def test_get_word_info_failure(mock_process_german_words):
    """Test failure case where process_german_words returns empty list."""
    word = "Fehlerwort"
    expected_empty_result = {
        "word": word,
        "word_translation": "",
        "phrase": "",
        "translation": "",
        "word_type": "unknown", # Specific default for this function
        "conjugation": "",
        "case_info": "",
        "gender": "",
        "plural": "",
        "additional_info": "",
        "related_words": ""
    }

    result = llm_generator.get_word_info(word)

    mock_process_german_words.assert_called_once_with([word])
    assert result == expected_empty_result

# --- Tests for process_words_file ---

@patch('src.llm_generator.format_for_anki_import')
@patch('src.llm_generator.process_german_words')
@patch('builtins.open', new_callable=mock_open)
@patch('pathlib.Path.exists', return_value=True) # Mock exists to return True
def test_process_words_file_success(mock_exists, mock_file, mock_process, mock_format, sample_words):
    """Test successful processing of an input file."""
    input_path_str = "dummy/input.txt"
    input_path = Path(input_path_str)
    mock_file().readlines.return_value = [f"{w}\n" for w in sample_words] # Simulate reading lines

    mock_processed_data = [{"word": w, "word_type": "mock"} for w in sample_words]
    mock_process.return_value = mock_processed_data

    mock_formatted_lines = [f"formatted_{w}" for w in sample_words]
    mock_format.return_value = mock_formatted_lines

    # Don't specify output_file_path to prevent CSV writing attempt
    formatted_lines, processed_data = llm_generator.process_words_file(input_file_path=input_path)

    mock_exists.assert_called_once() # Check that exists was called
    assert call(input_path, 'r', encoding='utf-8') in mock_file.call_args_list # Check if call exists
    mock_process.assert_called_once_with(sample_words) # Check that only words are passed
    mock_format.assert_called_once_with(mock_processed_data)
    assert formatted_lines == mock_formatted_lines
    assert processed_data == mock_processed_data

@patch('src.llm_generator.format_for_anki_import')
@patch('src.llm_generator.process_german_words')
@patch('builtins.open', new_callable=mock_open)
@patch('pathlib.Path.exists', return_value=True) # Mock exists to return True
def test_process_words_file_handles_empty_lines_and_strip(mock_exists, mock_file, mock_process, mock_format):
    """Test that empty lines and whitespace are handled correctly."""
    input_path_str = "dummy/input_strip.txt"
    input_path = Path(input_path_str)
    file_content = ["  word1  \n", "\n", "word2\n", "\tword3 \t\n", ""]
    expected_words_to_process = ["word1", "word2", "word3"]
    mock_file().readlines.return_value = file_content

    mock_processed_data = [{"word": w, "word_type": "mock"} for w in expected_words_to_process]
    mock_process.return_value = mock_processed_data
    mock_format.return_value = [f"formatted_{w}" for w in expected_words_to_process]

    formatted_lines, processed_data = llm_generator.process_words_file(input_file_path=input_path)

    mock_exists.assert_called_once() # Check that exists was called
    assert call(input_path, 'r', encoding='utf-8') in mock_file.call_args_list # Check if call exists
    mock_process.assert_called_once_with(expected_words_to_process) # Verify correct words processed
    mock_format.assert_called_once_with(mock_processed_data)
    assert len(formatted_lines) == len(expected_words_to_process)
    assert len(processed_data) == len(expected_words_to_process)

@patch('builtins.open', side_effect=FileNotFoundError("File not here")) # open still mocked in case exists check fails
@patch('pathlib.Path.exists', return_value=False) # Mock exists to return False
def test_process_words_file_input_not_found(mock_exists, mock_file, capsys):
    """Test handling when input file does not exist."""
    input_path = Path("nonexistent/input.txt")

    formatted_lines, processed_data = llm_generator.process_words_file(input_file_path=input_path)

    mock_exists.assert_called_once() # exists should be checked
    mock_file.assert_not_called() # Ensure open is not called
    assert formatted_lines == []
    assert processed_data == []
    captured = capsys.readouterr()
    assert f"Error: Input file not found at {input_path}" in captured.out

# Note: CSV writing functionality seems removed/commented out in the provided code.
# If it were active, tests like the one below would be needed.
# @patch('csv.writer')
# @patch('src.groq_generator.format_for_anki_import')
# @patch('src.groq_generator.process_german_words')
# @patch('builtins.open', new_callable=mock_open)
# def test_process_words_file_writes_csv(mock_file, mock_process, mock_format, mock_csv_writer, tmp_path, sample_words):
#     """Test that the CSV file is written correctly when output path is provided."""
#     input_path = Path("dummy/input.txt")
#     output_path = tmp_path / "output.csv"
#     mock_file().readlines.return_value = [f"{w}\n" for w in sample_words]

#     mock_processed_data = [
#         {"word": "Haus", "word_translation": "house", "phrase": "Das Haus", "translation": "The house", "word_type": "noun", "gender": "neuter", "plural": "Häuser", "conjugation": "", "case_info": "", "additional_info": "", "related_words": ""},
#         {"word": "laufen", "word_translation": "to run", "phrase": "Ich laufe", "translation": "I run", "word_type": "verb", "gender": "", "plural": "", "conjugation": "er läuft", "case_info": "", "additional_info": "", "related_words": ""},
#         {"word": "schnell", "word_translation": "fast", "phrase": "schnell", "translation": "fast", "word_type": "adjective", "gender": "", "plural": "", "conjugation": "", "case_info": "", "additional_info": "", "related_words": ""}
#     ]
#     mock_process.return_value = mock_processed_data
#     mock_format.return_value = ["formatted_line"] * len(sample_words) # Return value doesn't matter for CSV part

#     # Mock the CSV writer instance
#     mock_writer_instance = MagicMock()
#     mock_csv_writer.return_value = mock_writer_instance

#     # Call the function with an output path
#     groq_generator.process_words_file(input_file_path=input_path, output_file_path=output_path)

#     # Check that open was called for both input and output files
#     assert call(input_path, 'r', encoding='utf-8') in mock_file.call_args_list
#     assert call(output_path, 'w', newline='', encoding='utf-8') in mock_file.call_args_list

#     # Check that the CSV writer wrote the header and rows
#     expected_header = list(mock_processed_data[0].keys())
#     mock_writer_instance.writerow.assert_any_call(expected_header)
#     assert mock_writer_instance.writerow.call_count == 1 + len(mock_processed_data)
#     for row_data in mock_processed_data:
#         mock_writer_instance.writerow.assert_any_call(list(row_data.values()))
