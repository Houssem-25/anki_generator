"""
GUI for the Anki Card Generator.
Modern two-page interface with API setup and generation pages.
"""

import sys
import os
import threading
from pathlib import Path
from typing import List, Optional

# Try to import PyQt5
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QLineEdit, QPushButton, QFileDialog, QComboBox,
        QTextEdit, QCheckBox, QMessageBox, QProgressBar, QStackedWidget,
        QFrame, QScrollArea, QSpacerItem, QSizePolicy, QGraphicsDropShadowEffect
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
    from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QPalette, QLinearGradient, QPainter
    PYTQT5_AVAILABLE = True
except ImportError:
    PYTQT5_AVAILABLE = False

from config import get_config, get_processing_options, validate_config, setup_directories
from processor import create_processor
from structures import ProcessingOptions, ProgressUpdate


def run_gui_application():
    """Run the GUI application."""
    if not PYTQT5_AVAILABLE:
        print("PyQt5 is required for GUI. Install with: pip install PyQt5")
        return
    
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    
    window = AnkiGeneratorGUI()
    window.show()
    
    sys.exit(app.exec_())


class ModernButton(QPushButton):
    """Modern styled button with hover effects."""
    def __init__(self, text="", primary=False, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(40)
        self.primary = primary
        self.update_style()
        
    def update_style(self):
        if self.primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                               stop:0 #1976d2, stop:1 #42a5f5);
                    color: white;
                    border: none;
                    border-radius: 20px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                              stop:0 #1565c0, stop:1 #1976d2);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                              stop:0 #0d47a1, stop:1 #1565c0);
                }
                QPushButton:disabled {
                    background: #90caf9;
                    color: #e3f2fd;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #f5f5f5;
                    color: #424242;
                    border: 1px solid #e0e0e0;
                    border-radius: 20px;
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


class StylizedLineEdit(QLineEdit):
    """Modern styled line edit."""
    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder_text)
        self.setFixedHeight(40)
        self.setStyleSheet("""
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


class StylizedComboBox(QComboBox):
    """Modern styled combo box."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QComboBox {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: #fafafa;
                color: #424242;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QComboBox:hover {
                background-color: #f5f5f5;
                border: 2px solid #bbdefb;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: none;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                selection-background-color: #bbdefb;
                selection-color: #424242;
            }
        """)


class GlassCard(QFrame):
    """Glass card effect with drop shadow."""
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
    """Dark themed console output."""
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
        """Add a styled message to the console output."""
        color_map = {
            "info": "#f5f5f5",
            "success": "#81c784",
            "warning": "#ffb74d",
            "error": "#e57373"
        }
        color = color_map.get(message_type, "#f5f5f5")
        
        self.append(f'<span style="color:{color};">[{message_type.upper()}] {message}</span>')
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
        self.repaint()
        QApplication.processEvents()
        
    def clear_console(self):
        self.clear()


class ProcessingThread(QThread):
    """Thread for processing words in background."""
    progress_signal = pyqtSignal(object)  # ProgressUpdate
    finished_signal = pyqtSignal(object)  # ProcessingStats
    error_signal = pyqtSignal(str)
    
    def __init__(self, words: List[str], options: ProcessingOptions, output_file: str):
        super().__init__()
        self.words = words
        self.options = options
        self.output_file = output_file
    
    def run(self):
        """Run the processing in background thread."""
        try:
            from processor import create_processor
            
            processor = create_processor(self.options)
            
            def progress_callback(progress: ProgressUpdate):
                self.progress_signal.emit(progress)
            
            results = processor.process_words(self.words, progress_callback)
            
            # Save results to the user-specified output file
            processor.save_cards_to_file(results, self.output_file)
            
            self.finished_signal.emit(processor.get_stats())
            
        except Exception as e:
            self.error_signal.emit(str(e))


class ApiSetupPage(QWidget):
    """First page for API key setup."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        """Initialize the API setup page."""
        # Use scroll area for smaller screens
        scroll_area = QScrollArea(self)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Create content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setAlignment(Qt.AlignCenter)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)
        scroll_area.setWidget(content_widget)
        
        # Add logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("logo.png")
        if not logo_pixmap.isNull():
            logo_pixmap = logo_pixmap.scaledToWidth(200, Qt.SmoothTransformation)
            logo_label.setPixmap(logo_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(logo_label)
            content_layout.addSpacing(10)
        
        # Title
        title = QLabel("Anki Generator")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 5px;
        """)
        
        # Subtitle
        subtitle = QLabel("AI-Powered Flashcard Creation")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            font-size: 16px;
            color: #42a5f5;
            margin-bottom: 10px;
        """)
        
        # Description
        description = QLabel("Create beautiful Anki flashcards with AI-generated definitions, examples, and images")
        description.setAlignment(Qt.AlignCenter)
        description.setWordWrap(True)
        description.setStyleSheet("""
            font-size: 14px;
            color: #616161;
            margin-bottom: 20px;
            max-width: 500px;
        """)
        
        # API Keys card
        api_card = GlassCard()
        api_card.setMinimumWidth(250)
        api_card.setMaximumWidth(450)
        
        api_layout = QVBoxLayout(api_card)
        api_layout.setContentsMargins(20, 20, 20, 20)
        api_layout.setSpacing(10)
        
        # API Keys header
        api_header_layout = QHBoxLayout()
        api_title = QLabel("API Keys Setup")
        api_title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1976d2;
        """)
        
        key_icon_label = QLabel()
        key_icon_label.setFixedSize(24, 24)
        key_icon_label.setStyleSheet("""
            background-color: #1976d2;
            border-radius: 12px;
            padding: 4px;
        """)
        
        api_header_layout.addWidget(key_icon_label)
        api_header_layout.addWidget(api_title)
        api_header_layout.addStretch()
        api_layout.addLayout(api_header_layout)
        
        # API description
        api_description = QLabel("Configure your API credentials to power the AI features.")
        api_description.setWordWrap(True)
        api_description.setStyleSheet("""
            font-size: 12px;
            color: #616161;
            margin-bottom: 8px;
        """)
        api_layout.addWidget(api_description)
        
        # Groq API Key container
        groq_container = QFrame()
        groq_container.setObjectName("GroqContainer")
        groq_container.setMinimumWidth(230)
        groq_container.setMaximumHeight(140)
        groq_container.setStyleSheet("""
            #GroqContainer {
                background-color: white;
                border-radius: 12px;
                padding: 8px;
                border: 1px solid #e0e0e0;
            }
            #GroqContainer:hover {
                border: 1px solid #2196f3;
                background-color: rgba(240, 247, 255, 0.5);
            }
        """)
        
        groq_layout = QVBoxLayout(groq_container)
        groq_layout.setContentsMargins(10, 8, 10, 8)
        groq_layout.setSpacing(6)  # Increased spacing for consistency
        
        groq_header = QHBoxLayout()
        groq_label = QLabel("Groq API Key")
        groq_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #1565c0;
        """)
        
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
            font-size: 11px;
            color: #757575;
            margin-bottom: 8px;
        """)
        
        # API Key input
        groq_input_label = QLabel("API Key:")
        groq_input_label.setStyleSheet("""
            font-size: 12px;
            color: #424242;
            font-weight: bold;
            margin-top: 4px;
        """)
        
        self.groq_input = StylizedLineEdit("Enter your Groq API key")
        self.groq_input.setEchoMode(QLineEdit.Password)
        
        groq_layout.addLayout(groq_header)
        groq_layout.addWidget(groq_help)
        groq_layout.addWidget(groq_input_label)
        groq_layout.addWidget(self.groq_input)
        
        # Cloudflare container
        cf_container = QFrame()
        cf_container.setObjectName("CFContainer")
        cf_container.setMinimumWidth(230)
        cf_container.setMaximumHeight(240)  # Increased height to prevent text occlusion
        cf_container.setStyleSheet("""
            #CFContainer {
                background-color: white;
                border-radius: 12px;
                padding: 8px;
                border: 1px solid #e0e0e0;
            }
            #CFContainer:hover {
                border: 1px solid #2196f3;
                background-color: rgba(240, 247, 255, 0.5);
            }
        """)
        
        cf_layout = QVBoxLayout(cf_container)
        cf_layout.setContentsMargins(10, 8, 10, 8)
        cf_layout.setSpacing(6)  # Increased spacing for better layout
        
        cf_header = QHBoxLayout()
        cf_label = QLabel("Cloudflare Credentials")
        cf_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #1565c0;
        """)
        
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
        cf_description.setMinimumHeight(40)  # Ensure enough height for the text
        cf_description.setStyleSheet("""
            font-size: 11px;
            color: #757575;
            margin-bottom: 12px;
            padding: 2px;
        """)
        
        # Account ID section
        cf_account_label = QLabel("Cloudflare Account ID:")
        cf_account_label.setStyleSheet("""
            font-size: 12px;
            color: #424242;
            font-weight: bold;
            margin-top: 8px;
        """)
        
        self.cf_account_input = StylizedLineEdit("Enter your Cloudflare Account ID")
        
        # API Token section
        cf_token_label = QLabel("Cloudflare API Token:")
        cf_token_label.setStyleSheet("""
            font-size: 12px;
            color: #424242;
            font-weight: bold;
            margin-top: 12px;
        """)
        
        self.cf_token_input = StylizedLineEdit("Enter your Cloudflare API Token")
        self.cf_token_input.setEchoMode(QLineEdit.Password)
        
        cf_layout.addLayout(cf_header)
        cf_layout.addWidget(cf_description)
        cf_layout.addWidget(cf_account_label)
        cf_layout.addWidget(self.cf_account_input)
        cf_layout.addWidget(cf_token_label)
        cf_layout.addWidget(self.cf_token_input)
        
        # Add containers to API card
        api_layout.addWidget(groq_container)
        api_layout.addWidget(cf_container)
        
        # Get started button
        get_started_btn = ModernButton("Get Started", primary=True)
        get_started_btn.setMinimumHeight(40)
        get_started_btn.setMinimumWidth(150)
        get_started_btn.clicked.connect(self.start_application)
        
        # Button container
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setAlignment(Qt.AlignCenter)
        button_layout.addWidget(get_started_btn)
        button_layout.setContentsMargins(0, 15, 0, 0)
        
        # Add components to content layout
        content_layout.addWidget(title)
        content_layout.addWidget(subtitle)
        content_layout.addWidget(description)
        content_layout.addWidget(api_card)
        content_layout.addWidget(button_container)
        content_layout.addStretch()
    
    def start_application(self):
        """Validate and set API keys, then switch to generation page."""
        credentials = {
            'groq_api_key': self.groq_input.text().strip(),
            'cf_account_id': self.cf_account_input.text().strip(),
            'cf_api_token': self.cf_token_input.text().strip()
        }
        
        # Check if required API key is provided
        if not credentials['groq_api_key']:
            QMessageBox.warning(self.parent, "Missing API Key", "Groq API key is required to use this application.")
            return
        
        # Set environment variables
        os.environ["GROQ_API_KEY"] = credentials['groq_api_key']
        if credentials['cf_account_id'] and credentials['cf_api_token']:
            os.environ["CLOUDFLARE_ACCOUNT_ID"] = credentials['cf_account_id']
            os.environ["CLOUDFLARE_API_TOKEN"] = credentials['cf_api_token']
        
        # Switch to generation page
        self.parent.stacked_widget.setCurrentIndex(1)


class GenerationPage(QWidget):
    """Second page for card generation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        """Initialize the generation page."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Logo as a floating widget above the content
        logo_label = QLabel(self)
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
            self.generator_logo = logo_label
        
        # Title
        title = QLabel("Card Generator")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #1976d2;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)
        
        # Input section card
        input_card = GlassCard()
        input_layout = QVBoxLayout(input_card)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(15)
        
        input_title = QLabel("Input Settings")
        input_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1976d2;")
        input_layout.addWidget(input_title)
        
        # Input text area
        input_text_label = QLabel("Enter vocabulary words (one per line):")
        input_text_label.setStyleSheet("font-weight: bold; color: #424242;")
        self.input_text_edit = QTextEdit()
        self.input_text_edit.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                background-color: #fafafa;
                color: #424242;
                selection-background-color: #bbdefb;
            }
            QTextEdit:focus {
                border: 2px solid #2196f3;
                background-color: white;
            }
            QTextEdit:hover {
                background-color: #f5f5f5;
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
        output_file_label.setStyleSheet("font-weight: bold; color: #424242;")
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
        language_label.setStyleSheet("font-weight: bold; color: #424242;")
        self.language_combo = StylizedComboBox()
        languages = ["English", "Arabic", "Spanish", "French", "German", "Italian", "Portuguese", 
                    "Russian", "Japanese", "Chinese", "Korean", "Dutch", "Swedish", "Turkish"]
        self.language_combo.addItems(languages)
        self.language_combo.setMinimumWidth(150)
        
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo, 1)
        language_layout.addStretch()
        
        # Generate images checkbox
        self.generate_images_checkbox = QCheckBox("Generate images for cards")
        self.generate_images_checkbox.setChecked(False)
        self.generate_images_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #424242;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #e0e0e0;
                border-radius: 3px;
                background-color: #fafafa;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2196f3;
                border-radius: 3px;
                background-color: #2196f3;
            }
        """)
        
        # Enable checkbox if Cloudflare credentials are available
        if os.environ.get("CLOUDFLARE_ACCOUNT_ID") and os.environ.get("CLOUDFLARE_API_TOKEN"):
            self.generate_images_checkbox.setEnabled(True)
            self.generate_images_checkbox.setToolTip("Generate images for each vocabulary word")
        else:
            self.generate_images_checkbox.setEnabled(False)
            self.generate_images_checkbox.setToolTip("Cloudflare credentials are required for image generation")
        
        # Add settings to input layout
        input_layout.addLayout(output_file_layout)
        input_layout.addLayout(language_layout)
        input_layout.addWidget(self.generate_images_checkbox)
        
        # Generate button
        generate_btn = ModernButton("Generate Cards", primary=True)
        generate_btn.clicked.connect(self.start_generation)
        input_layout.addWidget(generate_btn)
        
        layout.addWidget(input_card)
        
        # Output section card
        output_card = GlassCard()
        output_layout = QVBoxLayout(output_card)
        output_layout.setContentsMargins(20, 20, 20, 20)
        output_layout.setSpacing(15)
        
        output_title = QLabel("Generation Progress")
        output_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1976d2;")
        output_layout.addWidget(output_title)
        
        # Console output
        console_label = QLabel("Console Output:")
        console_label.setStyleSheet("font-weight: bold; color: #424242;")
        self.console = ConsoleOutput()
        
        output_layout.addWidget(console_label)
        output_layout.addWidget(self.console)
        
        layout.addWidget(output_card)
        
        # Define resize event to position logo properly
        original_resize = self.resizeEvent
        def custom_resize_event(event):
            if hasattr(self, 'generator_logo') and hasattr(self.generator_logo, 'pixmap') and not self.generator_logo.pixmap().isNull():
                # Position the logo at the top right with a margin
                self.generator_logo.move(self.width() - self.generator_logo.pixmap().width() - 20, 20)
            # Call original resize event 
            if original_resize:
                original_resize(event)
        
        self.resizeEvent = custom_resize_event
    
    def browse_output_file(self):
        """Browse for output file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Select Output File", "", "Anki Package (*.txt);;All Files (*)"
        )
        if file_path:
            if not file_path.endswith('.txt'):
                file_path += '.txt'
            self.output_file_edit.setText(file_path)
            self.console.append_message(f"Output file selected: {file_path}")
    
    def start_generation(self):
        """Start the generation process."""
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
        self.console.clear_console()
        
        # Parse words
        words = [word.strip() for word in input_text.split('\n') if word.strip()]
        
        # Create processing options
        options = ProcessingOptions(
            target_language=language,
            generate_audio=True,
            generate_images=generate_images,
            anki_media_path=None,
            debug_mode=True
        )
        
        # Start worker thread
        self.worker_thread = ProcessingThread(words, options, output_file)
        self.worker_thread.progress_signal.connect(self.update_progress)
        self.worker_thread.finished_signal.connect(self.process_finished)
        self.worker_thread.error_signal.connect(self.process_error)
        self.worker_thread.start()
        
        # Disable generate button while processing
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Generate Cards":
                btn.setEnabled(False)
    
    def update_progress(self, progress_update):
        """Update progress display."""
        if hasattr(progress_update, 'message'):
            self.console.append_message(progress_update.message)
        if hasattr(progress_update, 'current') and hasattr(progress_update, 'total'):
            percentage = int((progress_update.current / progress_update.total) * 100)
            self.console.append_message(f"Progress: {percentage}%")
    
    def process_finished(self, stats):
        """Handle process completion."""
        # Re-enable generate button
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Generate Cards":
                btn.setEnabled(True)
        
        self.console.append_message("Card generation completed successfully!", "success")
        QMessageBox.information(self, "Success", "Card generation completed successfully!")
    
    def process_error(self, error_message):
        """Handle process errors."""
        # Re-enable generate button
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Generate Cards":
                btn.setEnabled(True)
        
        self.console.append_message(f"Error: {error_message}", "error")
        QMessageBox.warning(self, "Error", f"Card generation failed: {error_message}")


class AnkiGeneratorGUI(QMainWindow):
    """Main GUI window with two-page structure."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Anki Generator")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Set window icon
        app_icon = QIcon("logo.png")
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        
        # Initialize UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create stacked widget for two pages
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        api_setup_page = ApiSetupPage(self)
        generation_page = GenerationPage(self)
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(api_setup_page)
        self.stacked_widget.addWidget(generation_page)
        
        # Add stacked widget to main layout
        layout.addWidget(self.stacked_widget)
        
        # Start with API setup page
        self.stacked_widget.setCurrentIndex(0)
