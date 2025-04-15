"""Main entry point for the Anki Card Generator application."""

import sys
from pathlib import Path

# Add the project root to the Python path for absolute imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import the main application class
from src.app import AnkiGeneratorApp

def main():
    """Initializes and runs the Anki Generator application."""
    app = AnkiGeneratorApp()
    app.run()

if __name__ == "__main__":
    main()