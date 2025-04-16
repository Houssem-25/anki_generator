import sys
import os
import traceback # For error logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QDialog, QTextEdit, QProgressBar, 
    QComboBox, QMessageBox, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path

# --- Backend Imports --- 
# Add the project root to the path if needed
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import our backend
try:
    from src.app import AnkiGeneratorApp as BackendApp
except ImportError as e:
    print(f"Error importing backend from src.app: {e}")
    try:
        # Alternative: try direct import if run directly from src
        from app import AnkiGeneratorApp as BackendApp
    except ImportError as e:
        print(f"Error importing backend from app: {e}")
        # Fallback dummy class
        class BackendApp:
            def __init__(self, *args, **kwargs): 
                print("Warning: BackendApp not loaded!")
                self.args = type('Args', (), {'target_language': 'english'})() 
            def setup(self, *args, **kwargs): 
                print("Dummy setup called")
                return
            def run_processing_loop_iterator(self, *args, **kwargs):
                print("Backend not loaded, cannot generate.")
                yield {"type": "error", "message": "Backend not loaded"}
            def get_summary(self):
                return "Backend not loaded."
            def get_total_words(self): return 0
            def get_processed_count(self): return 0

# --- API Key Dialog (Mostly unchanged) ---
class ApiKeyDialog(QDialog):
    """Dialog to get API keys from the user."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Credentials Setup")
        self.setModal(True)
        layout = QVBoxLayout(self)
        # ... (Groq and Cloudflare fields - unchanged) ...
        layout.addWidget(QLabel("Groq API Key (Required):"))
        self.groq_api_key_edit = QLineEdit()
        self.groq_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.groq_api_key_edit)
        layout.addWidget(QLabel("Cloudflare Account ID (Optional, for Images):"))
        self.cf_account_id_edit = QLineEdit()
        layout.addWidget(self.cf_account_id_edit)
        layout.addWidget(QLabel("Cloudflare API Token (Optional, for Images):"))
        self.cf_api_token_edit = QLineEdit()
        self.cf_api_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.cf_api_token_edit)
        self._load_existing_credentials()
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save & Continue")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)
        self.setMinimumWidth(400)

    def _load_existing_credentials(self):
        groq_key = os.environ.get("GROQ_API_KEY")
        cf_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        cf_token = os.environ.get("CLOUDFLARE_API_TOKEN")
        if groq_key: self.groq_api_key_edit.setText(groq_key)
        if cf_id: self.cf_account_id_edit.setText(cf_id)
        if cf_token: self.cf_api_token_edit.setText(cf_token)
            
    def get_credentials(self):
        return {
            "groq_api_key": self.groq_api_key_edit.text().strip(),
            "cf_account_id": self.cf_account_id_edit.text().strip(),
            "cf_api_token": self.cf_api_token_edit.text().strip()
        }

# --- Worker Thread --- 
class GeneratorWorker(QThread):
    """Runs the Anki generation in a separate thread."""
    progress = pyqtSignal(int)  # Signal for progress percentage
    log = pyqtSignal(str)       # Signal for logging messages
    finished = pyqtSignal(bool, str) # Signal for completion (success_flag, summary_message)

    def __init__(self, words: list[str], output_file: str, generate_images: bool, parent=None):
        super().__init__(parent)
        self.words = words
        self.output_file = output_file
        self.generate_images = generate_images
        self.backend_app = None

    def run(self):
        """The main logic executed in the thread."""
        try:
            self.log.emit("--- Initializing Backend --- ")
            # --- Prepare Mock Args for Backend --- 
            # We create a simple object that mimics argparse Namespace
            mock_args = type('Args', (), {
                'target_language': 'english',  # Default to English
                'input': None,                 # Not reading from file in GUI mode
                'output': Path(self.output_file),
                'anki_media_path': os.environ.get("ANKI_MEDIA_PATH"), 
                'no_audio': False, 
                'no_image': not self.generate_images,  # Use the checkbox value
                'shuffle': True
            })()
            
            self.backend_app = BackendApp(mock_args)
            self.backend_app.setup(input_words=self.words)
            
            total_words = self.backend_app.get_total_words()
            if total_words == 0:
                self.log.emit("No words to process.")
                self.finished.emit(True, "No words provided.")
                return

            self.log.emit(f"--- Starting Processing Loop for {total_words} Words --- ")
            self.log.emit(f"--- Output will be saved to: {self.output_file} ---")
            
            # Use an iterator if your backend supports it for progress
            processed_count = 0
            for result in self.backend_app.run_processing_loop_iterator():
                if result.get("type") == "log":
                    self.log.emit(result["message"])
                elif result.get("type") == "progress":
                     processed_count = result.get("processed", processed_count + 1)
                     percent = int((processed_count / total_words) * 100)
                     self.progress.emit(percent)
                elif result.get("type") == "error":
                     self.log.emit(f"ERROR: {result['message']}")
                
            # Ensure progress reaches 100% if loop finishes normally
            self.progress.emit(100)
            summary = self.backend_app.get_summary()
            self.log.emit("--- Generation Complete --- ")
            self.finished.emit(True, summary)

        except Exception as e:
            self.log.emit(f"--- Critical Error During Generation ---")
            self.log.emit(traceback.format_exc()) # Log full traceback
            self.finished.emit(False, f"An unexpected error occurred: {e}")

# --- Main Application Window --- 
class AnkiGeneratorApp(QMainWindow):
    """Main application window."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anki Card Generator")
        self.setGeometry(100, 100, 600, 550)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # --- Word Input ---
        self.layout.addWidget(QLabel("Enter words (one per line):"))
        self.word_input = QTextEdit()
        self.word_input.setPlaceholderText("Öffentlichkeit\nAusgehen\n...")
        self.layout.addWidget(self.word_input)

        # --- Options Layout ---
        options_layout = QHBoxLayout()
        
        # --- Image Generation Checkbox ---
        self.image_checkbox = QCheckBox("Generate Images")
        self.image_checkbox.setChecked(True)  # Default to enabled
        options_layout.addWidget(self.image_checkbox)
        
        options_layout.addStretch()
        self.layout.addLayout(options_layout)

        # --- Output File Selection --- 
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output File:"))
        self.output_file_edit = QLineEdit()
        # Set a default path (optional)
        default_output_dir = os.path.join(os.getcwd(), "anki_output") 
        os.makedirs(default_output_dir, exist_ok=True)
        default_output_path = os.path.join(default_output_dir, "anki_deck.txt")
        self.output_file_edit.setText(default_output_path)
        output_layout.addWidget(self.output_file_edit)
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.select_output_file)
        output_layout.addWidget(self.browse_button)
        self.layout.addLayout(output_layout)

        # --- Generate Button ---
        self.generate_button = QPushButton("Generate Anki Deck")
        self.generate_button.clicked.connect(self.start_generation) # Connect the button
        self.layout.addWidget(self.generate_button)

        # --- Progress Bar ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        # --- Log/Debug Output ---
        self.layout.addWidget(QLabel("Logs:"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)
        
        self.worker = None # To hold the worker thread instance
        
    def closeEvent(self, event):
        """Handle window close event - ensure worker thread is terminated."""
        if self.worker and self.worker.isRunning():
            self.worker.quit()  # Request the thread to quit
            self.worker.wait()  # Wait for it to finish (with timeout)
        event.accept()  # Allow the window to close

    def select_output_file(self):
        """Opens a dialog to select the output Anki deck file."""
        current_path = self.output_file_edit.text()
        # Use directory of current path as starting point for dialog
        start_dir = os.path.dirname(current_path) if current_path else os.getcwd()
        
        # Open Save File dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Select Output Anki Deck File", 
            start_dir, # Starting directory
            "Text Files (*.txt);;All Files (*)" # File filters
        )
        
        if file_path: # If the user selected a file (didn't cancel)
            self.output_file_edit.setText(file_path)

    def log_message(self, message):
        """Appends a message to the log display (Slot)."""
        self.log_output.append(message)
        # No need for processEvents here, signals handle UI updates correctly

    def show_error(self, title, message):
         QMessageBox.critical(self, title, message)

    def start_generation(self):
        """Slot to start the generation process."""
        words_text = self.word_input.toPlainText().strip()
        if not words_text:
            self.show_error("Input Error", "Please enter at least one word.")
            return
            
        words = [line.strip() for line in words_text.split('\n') if line.strip()]
        if not words:
             self.show_error("Input Error", "No valid words found after splitting lines.") 
             return

        output_file = self.output_file_edit.text().strip()
        generate_images = self.image_checkbox.isChecked()

        if not output_file:
            self.show_error("Input Error", "Please specify an output file path.")
            return
            
        # Ensure the output directory exists before starting the worker
        output_dir = os.path.dirname(output_file)
        try:
            if output_dir: # Only create if path includes a directory
                os.makedirs(output_dir, exist_ok=True)
        except OSError as e:
            self.show_error("Output Error", f"Could not create output directory '{output_dir}':\n{e}")
            return

        # --- Prepare UI for generation ---
        self.log_output.clear() # Clear previous logs
        self.progress_bar.setValue(0)
        self.generate_button.setEnabled(False) # Disable button during run
        
        # Log startup information
        self.log_message(f"Starting generation for {len(words)} words...")
        if generate_images:
            self.log_message("✅ Image generation is ENABLED")
            if not (os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN")):
                self.log_message("⚠️ Warning: Cloudflare credentials missing - images may not be generated")
        else:
            self.log_message("❌ Image generation is DISABLED")

        # --- Create and start worker ---
        self.worker = GeneratorWorker(words, output_file, generate_images)
        
        # Connect worker signals to GUI slots
        self.worker.log.connect(self.log_message)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.generation_finished)
        
        self.worker.start() # Start the thread
    
    def update_progress(self, value):
        """Slot to update the progress bar."""
        self.progress_bar.setValue(value)

    def generation_finished(self, success, message):
        """Slot called when the worker thread finishes."""
        self.log_message(message) # Log the final summary/error
        self.progress_bar.setValue(100) # Set to 100% on completion
        self.generate_button.setEnabled(True) # Re-enable the button
        self.worker = None # Release the worker instance
        
        if success:
            output_file = self.output_file_edit.text()
            QMessageBox.information(self, "Success", f"Anki deck generation finished!\nOutput saved to: {output_file}\n{message}")
        else:
            self.show_error("Error", f"Anki deck generation failed.\n{message}")

# --- Main Execution Logic (Mostly unchanged) --- 
if __name__ == '__main__':
    app = QApplication(sys.argv)
    api_dialog = ApiKeyDialog()
    
    if api_dialog.exec() == QDialog.DialogCode.Accepted:
        credentials = api_dialog.get_credentials()
        if not credentials['groq_api_key']:
             QMessageBox.critical(None, "Error", "Groq API Key is required.")
             sys.exit(1)
        
        # Set environment variables for the backend to potentially pick up
        os.environ["GROQ_API_KEY"] = credentials['groq_api_key']
        if credentials['cf_account_id']:
            os.environ["CLOUDFLARE_ACCOUNT_ID"] = credentials['cf_account_id']
        if credentials['cf_api_token']:
             os.environ["CLOUDFLARE_API_TOKEN"] = credentials['cf_api_token']
             
        print("Credentials accepted.") # Console log

        main_window = AnkiGeneratorApp()
        main_window.show()
        sys.exit(app.exec())
    else:
        print("API Key setup cancelled. Exiting.")
        sys.exit(0) 