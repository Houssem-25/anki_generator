#!/usr/bin/env python3
"""
Main entry point for the Anki Card Generator.
This file serves as the entry point when running the application.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main function from src.main
from app import main

if __name__ == "__main__":
    main()
