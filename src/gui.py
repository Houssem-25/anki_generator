import sys
import os
import threading
import random
import tempfile
import subprocess
import time
from typing import List, Optional, Dict, Any, Tuple
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox, 
                            QProgressBar, QTextEdit, QFrame, QSplitter, QStackedWidget,
                            QScrollArea, QGridLayout, QToolButton, QSpacerItem, QSizePolicy,
                            QTabWidget, QGraphicsDropShadowEffect, QMessageBox, QDialog, QCheckBox, QShortcut, QStackedLayout)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer, QRect, QThread, QPoint, pyqtProperty
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette, QPixmap, QLinearGradient, QPainter, QPainterPath, QCursor, QKeySequence
import qdarkstyle

# API Key Dialog for collecting necessary API keys
class ApiKeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Setup")
        self.setMinimumWidth(500)
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        
        layout = QVBoxLayout()
        
        # Add explanation text
        explanation = QLabel("This application requires API keys to function. Only the Groq API key is required. Cloudflare credentials are optional for image generation capabilities.")
        explanation.setWordWrap(True)
        explanation.setStyleSheet("margin-bottom: 15px;")
        layout.addWidget(explanation)
        
        # Groq API Key (required)
        groq_layout = QVBoxLayout()
        groq_label = QLabel("Groq API Key (required):")
        groq_help = QLabel("Get your Groq API key at: https://console.groq.com/keys")
        groq_help.setStyleSheet("font-size: 11px; color: #90CAF9;")
        self.groq_input = QLineEdit()
        self.groq_input.setEchoMode(QLineEdit.Password)
        self.groq_input.setPlaceholderText("Enter your Groq API key")
        self.groq_input.setMinimumHeight(30)
        self.groq_input.setMaximumHeight(30)
        groq_layout.addWidget(groq_label)
        groq_layout.addWidget(groq_help)
        groq_layout.addWidget(self.groq_input)
        
        # Cloudflare Account ID (optional)
        cf_account_layout = QVBoxLayout()
        cf_account_label = QLabel("Cloudflare Account ID (optional, for image generation):")
        cf_help = QLabel("Optional: For image generation capabilities. Get credentials at: https://dash.cloudflare.com")
        cf_help.setStyleSheet("font-size: 11px; color: #90CAF9;")
        self.cf_account_input = QLineEdit()
        self.cf_account_input.setPlaceholderText("Enter your Cloudflare Account ID (optional)")
        self.cf_account_input.setMinimumHeight(30)
        self.cf_account_input.setMaximumHeight(30)
        cf_account_layout.addWidget(cf_account_label)
        cf_account_layout.addWidget(cf_help)
        cf_account_layout.addWidget(self.cf_account_input)
        
        # Cloudflare API Token (optional)
        cf_token_layout = QVBoxLayout()
        cf_token_label = QLabel("Cloudflare API Token (optional, for image generation):")
        self.cf_token_input = QLineEdit()
        self.cf_token_input.setEchoMode(QLineEdit.Password)
        self.cf_token_input.setPlaceholderText("Enter your Cloudflare API token (optional)")
        self.cf_token_input.setMinimumHeight(30)
        self.cf_token_input.setMaximumHeight(30)
        cf_token_layout.addWidget(cf_token_label)
        cf_token_layout.addWidget(self.cf_token_input)
        
        # Button layout
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        
        # Connect buttons
        self.cancel_button.clicked.connect(self.reject)
        self.ok_button.clicked.connect(self.validate_and_accept)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)
        
        # Add all layouts to main layout
        layout.addLayout(groq_layout)
        layout.addLayout(cf_account_layout)
        layout.addLayout(cf_token_layout)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def validate_and_accept(self):
        """Validate the required fields before accepting"""
        if not self.groq_input.text().strip():
            QMessageBox.warning(self, "Required Field", "Groq API key is required to use this application.")
            return
        self.accept()
    
    def get_credentials(self):
        """Return the entered credentials."""
        return {
            'groq_api_key': self.groq_input.text().strip(),
            'cf_account_id': self.cf_account_input.text().strip(),
            'cf_api_token': self.cf_token_input.text().strip()
        }

# List of available languages
LANGUAGES = [
    "English", "Arabic", "Spanish", "French", "German", "Italian", "Portuguese", 
    "Russian", "Japanese", "Chinese", "Korean", "Dutch", "Swedish", "Turkish"
]

class WorkerThread(QThread):
    progress_signal = pyqtSignal(int)
    console_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    word_processed_signal = pyqtSignal(dict)
    
    def __init__(self, input_text: str, output_file: str, target_language: str, generate_images: bool = False):
        super().__init__()
        self.input_text = input_text
        self.output_file = output_file
        self.target_language = target_language.lower()
        self.generate_images = generate_images
        self.processed_words = set()  # Keep track of processed words
        
    def run(self):
        try:
            self.console_signal.emit("Initializing language processor...")
            
            # Parse input words
            words = [word.strip() for word in self.input_text.split('\n') if word.strip()]
            word_count = len(words)
            self.console_signal.emit(f"Found {word_count} words to process")
            
            if word_count == 0:
                self.console_signal.emit("No words to process")
                self.finished_signal.emit(False, "No words provided")
                return
            
            # Create a temporary input file for the words
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_input_path = temp_file.name
                temp_file.write('\n'.join(words))
                self.console_signal.emit(f"Created temporary file with {word_count} words")
            
            # Create a temporary script that handles imports properly
            script_content = f"""
import os
import sys
import subprocess

print("Current working directory:", os.getcwd())

# Create a simple script that processes the words directly without imports
temp_output_file = "{self.output_file}"

# Run Python as a module with proper imports
cmd = [
    sys.executable,
    "-m",
    "src.main",  # Run as a module, not a script
    "-i", "{temp_input_path}",
    "-o", "{self.output_file}",
    "--target-language", "{self.target_language}"
]

# Add no-image flag if images are not requested
if not {self.generate_images}:
    cmd.append("--no-image")

print(f"Running command: {{' '.join(cmd)}}")

# Set PYTHONPATH to include the current directory
my_env = os.environ.copy()
my_env["PYTHONPATH"] = os.getcwd()  # This is critical for imports to work

# Use the modified environment
result = subprocess.run(cmd, capture_output=True, text=True, env=my_env)

# Print output
print(result.stdout)

# Print errors if any
if result.stderr:
    print(f"ERROR: {{result.stderr}}")

# Return the exit code
sys.exit(result.returncode)
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                temp_script_path = script_file.name
                script_file.write(script_content)
                self.console_signal.emit(f"Created temporary script to run processor")
            
            # Make sure parent directory for output file exists
            output_dir = os.path.dirname(self.output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            
            # Run the temporary script
            cmd = [sys.executable, temp_script_path]
            
            self.console_signal.emit(f"Running processor script...")
            
            # Start subprocess and monitor its output
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffering
                universal_newlines=True  # Ensure text mode with universal newlines
            )
            
            # Track progress
            progress = 0
            self.progress_signal.emit(progress)
            
            # Function to parse output from the main command
            def read_output(pipe, is_error=False):
                nonlocal progress
                for line in iter(pipe.readline, ''):
                    if not line:
                        break
                    
                    line = line.strip()
                    if not line:
                        continue
                        
                    if is_error:
                        self.console_signal.emit(f"ERROR: {line}")
                    else:
                        self.console_signal.emit(line)
                        
                        # Track progress based on specific markers in the output
                        # More aggressively track progress by checking for various word processing markers
                        if any(marker in line for marker in ["Processing word:", "Analyzing word:", "Processing:", "Word:"]):
                            # Try to get the word being processed
                            try:
                                # Extract the word being processed - handle multiple formats
                                if "Processing word:" in line:
                                    word = line.split("Processing word:")[1].strip()
                                elif "Analyzing word:" in line:
                                    word = line.split("Analyzing word:")[1].strip()
                                elif "Processing:" in line:
                                    word = line.split("Processing:")[1].strip()
                                elif "Word:" in line:
                                    word = line.split("Word:")[1].strip()
                                else:
                                    # In case no specific marker is found but we entered this branch
                                    # use a generic approach to find a potential word
                                    parts = line.split(":")
                                    if len(parts) > 1:
                                        word = parts[1].strip()
                                    else:
                                        # If all else fails, use the line itself (limited to first 20 chars)
                                        word = line[:20]
                                
                                # Update the set of processed words
                                if word not in self.processed_words:
                                    self.processed_words.add(word)
                                    
                                    # Calculate progress based on unique words processed
                                    # Leave 10% for final processing
                                    new_progress = int(90 * len(self.processed_words) / word_count)
                                    
                                    # Always emit progress signal for better updates
                                    if new_progress > progress:
                                        progress = new_progress
                                        self.progress_signal.emit(progress)
                                        # Force UI update
                                        self.console_signal.emit(f"Progress: {progress}% - Processing: {word}")
                                    
                                    # Create a minimal preview update
                                    self.word_processed_signal.emit({
                                        "word": word,
                                        "definition": "Processing...",
                                        "example": "",
                                        "translation": ""
                                    })
                            except Exception as e:
                                self.console_signal.emit(f"WARNING: Error tracking progress: {str(e)}")
                        
                        # Additional tracking for specific phases
                        elif "Successfully processed" in line and "word" in line:
                            # Try to extract the word
                            try:
                                word = line.split("Successfully processed")[1].split("'")[1].strip()
                                # Update progress if this is a new word
                                if word not in self.processed_words:
                                    self.processed_words.add(word)
                                    new_progress = int(90 * len(self.processed_words) / word_count)
                                    if new_progress > progress:
                                        progress = new_progress
                                        self.progress_signal.emit(progress)
                                        # Force UI update
                                        self.console_signal.emit(f"Progress: {progress}% - Completed: {word}")
                            except:
                                pass
                        
                        # Final processing phases
                        elif any(x in line.lower() for x in ["saving deck", "generating deck", "building deck"]):
                            new_progress = 95
                            if new_progress > progress:
                                progress = new_progress
                                self.progress_signal.emit(progress)
                                # Force UI update
                                self.console_signal.emit(f"Progress: {progress}% - Final processing...")
                                
                        elif any(x in line.lower() for x in ["saved deck", "successfully", "completed", "finished"]):
                            new_progress = 100
                            if new_progress > progress:
                                progress = new_progress
                                self.progress_signal.emit(progress)
                                # Force UI update
                                self.console_signal.emit(f"Progress: {progress}% - Completed!")
                        
                        # Intermediate updates to prevent long periods without progress updates
                        elif "..." in line or "." * 3 in line:
                            # Small increment for activity indicators to show the process is still active
                            new_progress = min(85, progress + 1)
                            if new_progress > progress:
                                progress = new_progress
                                self.progress_signal.emit(progress)
            
            # Start threads to read output
            stdout_thread = threading.Thread(target=read_output, args=(process.stdout,))
            stderr_thread = threading.Thread(target=read_output, args=(process.stderr, True))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for completion
            return_code = process.wait()
            stdout_thread.join()
            stderr_thread.join()
            
            # Clean up temp files
            try:
                os.unlink(temp_input_path)
                os.unlink(temp_script_path)
                self.console_signal.emit("Cleaned up temporary files")
            except Exception as e:
                self.console_signal.emit(f"Warning: Could not clean up temporary files: {e}")
            
            # Set final progress and status
            self.progress_signal.emit(100)
            
            if return_code == 0:
                # Try to read the results file to show preview
                try:
                    if os.path.exists(self.output_file):
                        with open(self.output_file, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            if first_line:
                                parts = first_line.split('\t')
                                if len(parts) >= 4:
                                    self.word_processed_signal.emit({
                                        "word": parts[0],
                                        "definition": parts[1],
                                        "example": parts[2],
                                        "translation": parts[3]
                                    })
                except Exception as e:
                    self.console_signal.emit(f"Failed to read output file: {e}")
                
                self.console_signal.emit(f"Successfully processed {word_count} words")
                self.finished_signal.emit(True, "Cards generated successfully!")
            else:
                self.console_signal.emit("Process failed with errors")
                self.finished_signal.emit(False, "Processing failed")
            
        except Exception as e:
            self.console_signal.emit(f"Error: {str(e)}")
            self.finished_signal.emit(False, str(e))

class ModernButton(QPushButton):
    def __init__(self, text="", icon=None, primary=False, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.primary = primary
        
        # Apply icon if provided
        if icon:
            self.setIcon(QIcon(icon))
            self.setIconSize(QSize(20, 20))
        
        # Set styles based on button type
        self.update_style()
        
        # Set up property for animation
        self.__color_value = 0
        
        # Hover animation
        self._animation = QPropertyAnimation(self, b"_color_value")
        self._animation.setDuration(200)
        
    def update_style(self):
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1e88e5;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #1976d2;
                }
                QPushButton:pressed {
                    background-color: #1565c0;
                }
                QPushButton:disabled {
                    background-color: #90caf9;
                    color: #e3f2fd;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f5f5f5;
                    color: #424242;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #eeeeee;
                    border: 1px solid #bdbdbd;
                }
                QPushButton:pressed {
                    background-color: #e0e0e0;
                }
                QPushButton:disabled {
                    background-color: #f5f5f5;
                    color: #bdbdbd;
                    border: 1px solid #eeeeee;
                }
            """)
    
    # Define property getter and setter
    def get_color_value(self):
        return self.__color_value
        
    def set_color_value(self, value):
        self.__color_value = value
        self.update()
    
    # Create the property
    _color_value = pyqtProperty(float, get_color_value, set_color_value)
        
    def enterEvent(self, event):
        self._animation.setStartValue(0)
        self._animation.setEndValue(1)
        self._animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._animation.setStartValue(1)
        self._animation.setEndValue(0)
        self._animation.start()
        super().leaveEvent(event)

class StylizedLineEdit(QLineEdit):
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: #f5f5f5;
                color: #424242;
                selection-background-color: #bbdefb;
            }
            QLineEdit:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QLineEdit:hover {
                background-color: #eeeeee;
            }
        """)

class StylizedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                background-color: #f5f5f5;
                color: #424242;
                selection-background-color: #bbdefb;
            }
            QComboBox:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QComboBox:hover {
                background-color: #eeeeee;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox::down-arrow {
                image: url(down-arrow.png);
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #bbdefb;
                selection-color: #424242;
            }
        """)

class AnimatedProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(10)
        self.setTextVisible(False)
        self.setValue(0)
        
        # Animated progress bar with gradient
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 5px;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                            stop:0 #2196f3, stop:1 #03a9f4);
            }
        """)
        
        # Pulse animation when indeterminate
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse_animation)
        
        # Optional shimmer effect
        self._shimmer_offset = 0
        self._shimmer_timer = QTimer(self)
        self._shimmer_timer.timeout.connect(self._update_shimmer)
        self._shimmer_timer.start(50)  # Update shimmer every 50ms
        
    def _pulse_animation(self):
        if self.value() >= 100:
            self.setValue(0)
        else:
            self.setValue(self.value() + 5)
            
    def _update_shimmer(self):
        self._shimmer_offset = (self._shimmer_offset + 5) % 100
        self.update()
        
    def startPulse(self):
        self._timer.start(100)
        
    def stopPulse(self):
        self._timer.stop()

class GlassCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlassCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            #GlassCard {
                background-color: rgba(255, 255, 255, 0.85);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

class ConsoleOutput(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #212121;
                color: #f5f5f5;
                border: none;
                border-radius: 10px;
                padding: 10px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
            }
            QScrollBar:vertical {
                background-color: #212121;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #424242;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #616161;
            }
        """)
        
    def append_message(self, message: str, message_type: str = "info"):
        """
        Add a styled message to the console output
        message_type can be 'info', 'success', 'warning' or 'error'
        """
        color_map = {
            "info": "#f5f5f5",
            "success": "#81c784",
            "warning": "#ffb74d",
            "error": "#e57373"
        }
        color = color_map.get(message_type, "#f5f5f5")
        
        timestamp = QApplication.instance().style().standardIcon(QApplication.style().SP_DialogApplyButton)
        self.append(f'<span style="color:{color};">[{message_type.upper()}] {message}</span>')
        
    def clear_console(self):
        self.clear()

class CardPreview(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Box)
        self.setMinimumHeight(250)
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # Set up layout
        layout = QVBoxLayout(self)
        
        # Card header
        header = QLabel("Card Preview")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 16px; color: #424242;")
        
        # Sample content
        self.content = QLabel("No cards generated yet")
        self.content.setAlignment(Qt.AlignCenter)
        self.content.setWordWrap(True)
        self.content.setStyleSheet("color: #757575; font-size: 14px;")
        
        # Add to layout
        layout.addWidget(header)
        layout.addWidget(self.content)
        
    def update_preview(self, word=None, definition=None, example=None, translation=None):
        if word:
            html = f"""
            <h2 style="color: #1976d2; text-align: center;">{word}</h2>
            <p style="color: #424242; margin-bottom: 10px;"><b>Definition:</b> {definition}</p>
            <p style="color: #424242; font-style: italic; margin-bottom: 10px;">"{example}"</p>
            <p style="color: #424242;"><b>Translation:</b> {translation}</p>
            """
            self.content.setText(html)
        else:
            self.content.setText("No cards generated yet")

class WelcomeScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Use a scroll area to handle smaller screen sizes
        scroll_area = QScrollArea(self)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create content widget that will be scrollable
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(50, 50, 50, 50)
        content_layout.setAlignment(Qt.AlignCenter)
        
        # Main layout just contains the scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        
        # Set the content widget as the scroll area's widget
        scroll_area.setWidget(content_widget)
        
        # Add logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaledToWidth(300, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(logo_label)
            content_layout.addSpacing(20)
        
        # Logo or title with modern styling
        title = QLabel("Anki Generator")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 10px;
            /* Remove text-shadow as it's causing warnings */
        """)
        
        # Subtitle with modern styling
        subtitle = QLabel("AI-Powered Flashcard Creation")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 18px;
            color: #42a5f5;
            margin-bottom: 15px;
        """)
        
        # Description
        description = QLabel("Create beautiful Anki flashcards with AI-generated definitions, examples, and images")
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("""
            font-size: 16px;
            color: #616161;
            margin-bottom: 40px;
            max-width: 600px;
        """)
        
        # API Keys section with attractive styling
        api_card = QFrame()
        api_card.setObjectName("ApiKeyCard")
        api_card.setMinimumWidth(300)  # Set minimum width
        api_card.setMaximumWidth(600)  # Add maximum width to prevent it from taking the full screen
        api_card.setStyleSheet("""
            #ApiKeyCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #f5f7fa, stop:1 #e4e8ec);
                border-radius: 20px;
                border: 1px solid rgba(200, 210, 230, 0.7);
            }
        """)
        
        # Add drop shadow effect to card
        shadow = QGraphicsDropShadowEffect(api_card)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        api_card.setGraphicsEffect(shadow)
        
        api_layout = QVBoxLayout(api_card)
        api_layout.setContentsMargins(30, 30, 30, 30)
        api_layout.setSpacing(20)
        
        # API Keys header with icon
        api_header_layout = QHBoxLayout()
        api_title = QLabel("API Keys Setup")
        api_title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #1976d2;
        """)
        
        # Icon for the header
        key_icon_label = QLabel()
        key_icon_label.setFixedSize(32, 32)
        # If you have an actual icon file, use this:
        # key_icon_label.setPixmap(QPixmap("icon/key.png").scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        key_icon_label.setStyleSheet("""
            background-color: #1976d2;
            border-radius: 16px;
            padding: 5px;
        """)
        
        api_header_layout.addWidget(key_icon_label)
        api_header_layout.addWidget(api_title)
        api_header_layout.addStretch()
        api_layout.addLayout(api_header_layout)
        
        # Description for API keys
        api_description = QLabel("Configure your API credentials to power the AI features.")
        api_description.setWordWrap(True)
        api_description.setStyleSheet("""
            font-size: 14px;
            color: #616161;
            margin-bottom: 10px;
        """)
        api_layout.addWidget(api_description)
        
        # Groq API Key (required) with modern styling
        groq_container = QFrame()
        groq_container.setObjectName("GroqContainer")
        groq_container.setMinimumWidth(280)
        groq_container.setMaximumHeight(160)  # Add maximum height
        groq_container.setStyleSheet("""
            #GroqContainer {
                background-color: white;
                border-radius: 12px;
                padding: 8px; /* Reduced from 10px */
                border: 1px solid #e0e0e0;
            }
            #GroqContainer:hover {
                border: 1px solid #2196f3;
                background-color: rgba(240, 247, 255, 0.5);
            }
        """)
        
        groq_layout = QVBoxLayout(groq_container)
        groq_layout.setContentsMargins(15, 12, 15, 12)  # Reduced vertical margins from 15 to 12
        groq_layout.setSpacing(6)  # Reduced from 8
        
        groq_header = QHBoxLayout()
        groq_label = QLabel("Groq API Key")
        groq_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1565c0;
        """)
        
        # Required badge
        required_badge = QLabel("REQUIRED")
        required_badge.setStyleSheet("""
            background-color: #ef5350;
            color: white;
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        
        groq_header.addWidget(groq_label)
        groq_header.addWidget(required_badge)
        groq_header.addStretch()
        
        groq_help = QLabel("Get your API key at: <a href='https://console.groq.com/keys' style='color: #1976d2;'>console.groq.com/keys</a>")
        groq_help.setOpenExternalLinks(True)
        groq_help.setStyleSheet("""
            font-size: 12px;
            color: #757575;
            margin-bottom: 5px;
        """)
        
        self.groq_input = QLineEdit()
        self.groq_input.setPlaceholderText("Enter your Groq API key")
        self.groq_input.setEchoMode(QLineEdit.Password)
        self.groq_input.setMinimumHeight(30)
        self.groq_input.setMaximumHeight(30)
        self.groq_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #fafafa;
                color: #424242;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QLineEdit:hover {
                background-color: #f5f5f5;
                border: 2px solid #bbdefb;
            }
        """)
        
        groq_layout.addLayout(groq_header)
        groq_layout.addWidget(groq_help)
        groq_layout.addWidget(self.groq_input)
        
        # Cloudflare section with modern styling
        cf_container = QFrame()
        cf_container.setObjectName("CFContainer")
        cf_container.setMinimumWidth(280)
        cf_container.setMaximumHeight(220)  # Add maximum height
        cf_container.setStyleSheet("""
            #CFContainer {
                background-color: white;
                border-radius: 12px;
                padding: 8px; /* Reduced from 10px */
                border: 1px solid #e0e0e0;
            }
            #CFContainer:hover {
                border: 1px solid #2196f3;
                background-color: rgba(240, 247, 255, 0.5);
            }
        """)
        
        cf_layout = QVBoxLayout(cf_container)
        cf_layout.setContentsMargins(15, 12, 15, 12)  # Reduced vertical margins
        cf_layout.setSpacing(6)  # Reduced spacing
        
        cf_header = QHBoxLayout()
        cf_label = QLabel("Cloudflare Credentials")
        cf_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1565c0;
        """)
        
        # Optional badge
        optional_badge = QLabel("OPTIONAL")
        optional_badge.setStyleSheet("""
            background-color: #7cb342;
            color: white;
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """)
        
        cf_header.addWidget(cf_label)
        cf_header.addWidget(optional_badge)
        cf_header.addStretch()
        
        cf_description = QLabel("Required only for image generation. Get your credentials at: <a href='https://dash.cloudflare.com' style='color: #1976d2;'>dash.cloudflare.com</a>")
        cf_description.setOpenExternalLinks(True)
        cf_description.setWordWrap(True)
        cf_description.setStyleSheet("""
            font-size: 12px;
            color: #757575;
            margin-bottom: 10px;
        """)
        
        # Account ID input
        cf_account_label = QLabel("Cloudflare Account ID:")
        cf_account_label.setStyleSheet("""
            font-size: 14px;
            color: #424242;
        """)
        
        self.cf_account_input = QLineEdit()
        self.cf_account_input.setPlaceholderText("Enter your Cloudflare Account ID")
        self.cf_account_input.setMinimumHeight(30)
        self.cf_account_input.setMaximumHeight(30)
        self.cf_account_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #fafafa;
                color: #424242;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QLineEdit:hover {
                background-color: #f5f5f5;
                border: 2px solid #bbdefb;
            }
        """)
        
        # API Token input
        cf_token_label = QLabel("Cloudflare API Token:")
        cf_token_label.setStyleSheet("""
            font-size: 14px;
            color: #424242;
            margin-top: 5px;
        """)
        
        self.cf_token_input = QLineEdit()
        self.cf_token_input.setPlaceholderText("Enter your Cloudflare API Token")
        self.cf_token_input.setEchoMode(QLineEdit.Password)
        self.cf_token_input.setMinimumHeight(30)
        self.cf_token_input.setMaximumHeight(30)
        self.cf_token_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #fafafa;
                color: #424242;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QLineEdit:hover {
                background-color: #f5f5f5;
                border: 2px solid #bbdefb;
            }
        """)
        
        cf_layout.addLayout(cf_header)
        cf_layout.addWidget(cf_description)
        cf_layout.addWidget(cf_account_label)
        cf_layout.addWidget(self.cf_account_input)
        cf_layout.addWidget(cf_token_label)
        cf_layout.addWidget(self.cf_token_input)
        
        # Add containers to API card layout
        api_layout.addWidget(groq_container)
        api_layout.addWidget(cf_container)
        
        # Get started button with enhanced styling
        get_started_btn = QPushButton("Get Started")
        get_started_btn.setCursor(QCursor(Qt.PointingHandCursor))
        get_started_btn.setMinimumHeight(50)
        get_started_btn.setMinimumWidth(200)
        get_started_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                           stop:0 #1976d2, stop:1 #42a5f5);
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #1565c0, stop:1 #1976d2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #0d47a1, stop:1 #1565c0);
            }
        """)
        get_started_btn.clicked.connect(lambda: self.start_application(parent))
        
        # Button container for centering
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(get_started_btn)
        button_layout.setContentsMargins(0, 30, 0, 0)
        
        # Add components to content_layout instead of layout
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addWidget(description)
        content_layout.addWidget(api_card)
        content_layout.addWidget(button_container)
        content_layout.addStretch()
        
    def start_application(self, parent):
        # Validate and set API keys
        credentials = {
            'groq_api_key': self.groq_input.text().strip(),
            'cf_account_id': self.cf_account_input.text().strip(),
            'cf_api_token': self.cf_token_input.text().strip()
        }
        
        # Check if required API key is provided
        if not credentials['groq_api_key']:
            QMessageBox.warning(parent, "Missing API Key", "Groq API key is required to use this application.")
            return
        
        # Set environment variables
        os.environ["GROQ_API_KEY"] = credentials['groq_api_key']
        if credentials['cf_account_id'] and credentials['cf_api_token']:
            os.environ["CLOUDFLARE_ACCOUNT_ID"] = credentials['cf_account_id']
            os.environ["CLOUDFLARE_API_TOKEN"] = credentials['cf_api_token']
        
        # Switch to the main interface
        parent.stacked_widget.setCurrentIndex(1)
        
        # Trigger resize event to position logo properly
        if hasattr(parent, 'generator_tab_logo'):
            generator_tab = parent.centralWidget().findChild(QTabWidget).widget(0)
            generator_tab.resizeEvent(None)

class AnkiGeneratorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Configure main window
        self.setWindowTitle("Anki Generator")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)  # Set a comfortable default size
        
        # Open maximized by default (fit to screen) instead of fullscreen
        self.showMaximized()
        self.is_maximized = True
        
        # Create F11 shortcut for toggling fullscreen/maximized
        fullscreen_shortcut = QShortcut(QKeySequence("F11"), self)
        fullscreen_shortcut.activated.connect(self.toggle_window_state)
        
        # Set window icon
        app_icon = QIcon("logo.png")
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        
        # Main layout
        self.setCentralWidget(QWidget())
        self.layout = QVBoxLayout(self.centralWidget())
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Create stacked widget for multiple screens
        self.stacked_widget = QStackedWidget()
        
        # Create welcome screen
        welcome_screen = WelcomeScreen(self)
        
        # Create main interface
        main_interface = QWidget()
        main_layout = QVBoxLayout(main_interface)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Set up tabbed interface
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: white;
                padding: 0px;  /* Remove padding */
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #eeeeee;
            }
        """)
        
        # Generator tab
        generator_tab = QWidget()
        generator_layout = QVBoxLayout(generator_tab)
        generator_layout.setContentsMargins(0, 0, 0, 0)
        generator_layout.setSpacing(0)
        
        # Create a parent widget to hold both the content and the logo
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Logo as a floating widget above the content
        # Create the logo widget first
        logo_label = QLabel(generator_tab)
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaledToWidth(120, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setStyleSheet("background: transparent; padding: 0; margin: 0; border: none;")
            logo_label.setAttribute(Qt.WA_TransparentForMouseEvents)  # Let clicks pass through
            
            # Initial position
            logo_label.move(20, 20)  # Set a fixed position with margin instead of 0,0
            
            # Make sure the logo stays on top
            logo_label.raise_()
            
            # Store the logo label for later access in resize events
            self.generator_tab_logo = logo_label
        
        # Create a splitter in the content widget
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # Left panel with scroll area for input
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Input panel
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(15)
        
        # Section title
        input_title = QLabel("Input Settings")
        input_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1976d2;")
        input_layout.addWidget(input_title)
        
        # Input text area
        input_text_label = QLabel("Enter vocabulary words (one per line):")
        self.input_text_edit = QTextEdit()
        self.input_text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                background-color: #f5f5f5;
                color: #424242;
                selection-background-color: #bbdefb;
            }
            QTextEdit:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QTextEdit:hover {
                background-color: #eeeeee;
            }
        """)
        self.input_text_edit.setPlaceholderText("Type or paste your vocabulary words here...\nExample:\nserendipity\nubiquitous\nephemeral")
        self.input_text_edit.setMinimumHeight(120)
        
        input_layout.addWidget(input_text_label)
        input_layout.addWidget(self.input_text_edit)
        
        # Output file selection
        output_file_layout = QHBoxLayout()
        output_file_label = QLabel("Output File:")
        output_file_label.setMinimumWidth(80)
        self.output_file_edit = StylizedLineEdit("Select output Anki file location...")
        self.output_file_edit.setReadOnly(True)
        self.output_file_edit.setMinimumWidth(150)
        browse_output_btn = ModernButton("Browse")
        browse_output_btn.setMinimumWidth(80)
        browse_output_btn.setMaximumWidth(80)
        browse_output_btn.clicked.connect(self.browse_output_file)
        
        output_file_layout.addWidget(output_file_label)
        output_file_layout.addWidget(self.output_file_edit, 1)
        output_file_layout.addWidget(browse_output_btn)
        
        # Language selection
        language_layout = QHBoxLayout()
        language_label = QLabel("Target Language:")
        language_label.setMinimumWidth(80)
        self.language_combo = StylizedComboBox()
        self.language_combo.addItems(LANGUAGES)
        self.language_combo.setMinimumWidth(150)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo, 1)
        language_layout.addStretch()
        
        # Image generation checkbox
        self.generate_images_checkbox = QCheckBox("Generate images for cards")
        self.generate_images_checkbox.setChecked(False)
        if not os.environ.get("CLOUDFLARE_ACCOUNT_ID") or not os.environ.get("CLOUDFLARE_API_TOKEN"):
            self.generate_images_checkbox.setEnabled(False)
            self.generate_images_checkbox.setToolTip("Cloudflare credentials are required for image generation")
        
        # Add settings to input layout
        input_layout.addLayout(output_file_layout)
        input_layout.addLayout(language_layout)
        input_layout.addWidget(self.generate_images_checkbox)
        
        # Action button
        generate_btn = ModernButton("Generate Cards", primary=True)
        generate_btn.clicked.connect(self.start_generation)
        input_layout.addWidget(generate_btn)
        
        # Add vertical spacer
        input_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Set the input widget as the scroll area's widget
        left_scroll.setWidget(input_widget)
        
        # Right panel with scroll area for output
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Output panel
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        output_layout.setContentsMargins(20, 20, 20, 20)
        output_layout.setSpacing(15)
        
        # Output title
        output_title = QLabel("Generation Progress")
        output_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1976d2;")
        output_layout.addWidget(output_title)
        
        # Progress bar
        self.progress_bar = AnimatedProgressBar()
        output_layout.addWidget(self.progress_bar)
        
        # Console output
        console_label = QLabel("Console Output:")
        console_label.setStyleSheet("font-weight: bold;")
        self.console = ConsoleOutput()
        
        output_layout.addWidget(console_label)
        output_layout.addWidget(self.console)
        
        # Card preview
        preview_label = QLabel("Card Preview:")
        preview_label.setStyleSheet("font-weight: bold;")
        self.card_preview = CardPreview()
        
        output_layout.addWidget(preview_label)
        output_layout.addWidget(self.card_preview)
        
        # Set the output widget as the scroll area's widget
        right_scroll.setWidget(output_widget)
        
        # Add scroll areas to splitter
        splitter.addWidget(left_scroll)
        splitter.addWidget(right_scroll)
        
        # Set initial sizes (50% each)
        splitter.setSizes([500, 500])
        
        # Add splitter to content layout
        content_layout.addWidget(splitter)
        
        # Add content widget to generator layout
        generator_layout.addWidget(content_widget)
        
        # Define resize event to position logo properly
        original_resize = generator_tab.resizeEvent
        def custom_resize_event(event):
            if hasattr(logo_label, 'pixmap') and not logo_label.pixmap().isNull():
                # Position the logo at the top right with a margin
                logo_label.move(generator_tab.width() - logo_label.pixmap().width() - 20, 20)
            # Call original resize event 
            if original_resize:
                original_resize(event)
        
        generator_tab.resizeEvent = custom_resize_event
        
        # Add tabs
        tabs.addTab(generator_tab, "Generator")
        
        # Add tabs to main layout
        main_layout.addWidget(tabs)
        
        # Add screens to stacked widget
        self.stacked_widget.addWidget(welcome_screen)
        self.stacked_widget.addWidget(main_interface)
        
        # Add stacked widget to main layout
        self.layout.addWidget(self.stacked_widget)
        
        # Initialize with welcome screen
        self.stacked_widget.setCurrentIndex(0)
        
        # Sample data for preview (will be removed in actual implementation)
        self.update_card_preview_sample()
        
    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", "", "Anki Package (*.txt);;All Files (*)"
        )
        if file_path:
            if not file_path.endswith('.txt'):
                file_path += '.txt'
            self.output_file_edit.setText(file_path)
            self.console.append_message(f"Output file selected: {file_path}")
    
    def start_generation(self):
        input_text = self.input_text_edit.toPlainText()
        output_file = self.output_file_edit.text()
        language = self.language_combo.currentText().lower()
        generate_images = self.generate_images_checkbox.isChecked()
        
        if not input_text.strip():
            QMessageBox.warning(self, "Missing Input", "Please enter vocabulary words.")
            return
            
        if not output_file:
            QMessageBox.warning(self, "Missing Output", "Please select an output file.")
            return
        
        # Clear previous output
        self.console.clear()
        self.progress_bar.setValue(0)
        
        # Start worker thread
        self.worker_thread = WorkerThread(input_text, output_file, language, generate_images)
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.console_signal.connect(self.update_console)
        self.worker_thread.finished_signal.connect(self.process_finished)
        self.worker_thread.word_processed_signal.connect(self.update_card_preview)
        self.worker_thread.start()
        
        # Disable generate button while processing
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Generate Cards":
                btn.setEnabled(False)
        
        # Show sample preview (to be replaced with actual data)
        self.update_card_preview_sample()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        # Force an immediate repaint of the progress bar
        self.progress_bar.repaint()
        # Process pending UI events to ensure progress bar is updated visually
        QApplication.processEvents()
    
    def update_console(self, message):
        if "error" in message.lower():
            self.console.append_message(message, "error")
        elif "success" in message.lower():
            self.console.append_message(message, "success")
        elif "warning" in message.lower():
            self.console.append_message(message, "warning")
        else:
            self.console.append_message(message)
    
    def process_finished(self, success, message):
        # Re-enable generate button
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Generate Cards":
                btn.setEnabled(True)
        
        if success:
            self.console.append_message(message, "success")
            QMessageBox.information(self, "Success", "Card generation completed successfully!")
        else:
            self.console.append_message(f"Process failed: {message}", "error")
            QMessageBox.warning(self, "Error", f"Card generation failed: {message}")
    
    def update_card_preview(self, result):
        # Update card preview with real processed data
        self.card_preview.update_preview(
            result.get("word", ""),
            result.get("definition", ""),
            result.get("example", ""),
            result.get("translation", "")
        )
    
    def update_card_preview_sample(self):
        # Sample data for preview - this is just for demonstration
        examples = [
            {
                "word": "Serendipity",
                "definition": "The occurrence and development of events by chance in a happy or beneficial way.",
                "example": "The discovery of penicillin was a serendipity, a happy accident.",
                "translation": "المصادفة السعيدة"
            },
            {
                "word": "Ephemeral",
                "definition": "Lasting for a very short time.",
                "example": "The ephemeral beauty of spring flowers.",
                "translation": "قصير الأمد"
            },
            {
                "word": "Ubiquitous",
                "definition": "Present, appearing, or found everywhere.",
                "example": "Smartphones are now ubiquitous in modern society.",
                "translation": "منتشر في كل مكان"
            }
        ]
        
        # Pick a random example
        example = random.choice(examples)
        self.card_preview.update_preview(
            example["word"], 
            example["definition"], 
            example["example"], 
            example["translation"]
        )

    def toggle_window_state(self):
        """Toggle between maximized and normal window mode"""
        if self.is_maximized:
            self.showNormal()
            self.is_maximized = False
        else:
            self.showMaximized()
            self.is_maximized = True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply dark style
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    # Set app font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = AnkiGeneratorApp()
    window.show()
    
    sys.exit(app.exec_())