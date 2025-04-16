#!/usr/bin/env python3
"""
Main entry point for the Anki Generator GUI.
Run this file to start the GUI interface.
"""

import sys
import os
from src.gui import QApplication, ApiKeyDialog, AnkiGeneratorApp, QDialog

def main():
    """Run the Anki Generator GUI application."""
    app = QApplication(sys.argv)
    
    # Show the API Key Dialog first
    api_dialog = ApiKeyDialog()
    
    if api_dialog.exec() == QDialog.DialogCode.Accepted:
        # Get and validate credentials
        credentials = api_dialog.get_credentials()
        if not credentials['groq_api_key']:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", "Groq API Key is required.")
            return 1
        
        # Set environment variables for backend
        os.environ["GROQ_API_KEY"] = credentials['groq_api_key']
        if credentials['cf_account_id']:
            os.environ["CLOUDFLARE_ACCOUNT_ID"] = credentials['cf_account_id']
        if credentials['cf_api_token']:
            os.environ["CLOUDFLARE_API_TOKEN"] = credentials['cf_api_token']
        
        # Launch the main application window
        main_window = AnkiGeneratorApp()
        main_window.show()
        return app.exec()
    else:
        print("API Key setup cancelled. Exiting.")
        return 0

if __name__ == '__main__':
    sys.exit(main()) 