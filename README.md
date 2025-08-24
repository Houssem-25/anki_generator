# # Anki Card Generator

<p align="center">
  <img src="logo.png" width="200">
</p>

## Description

Anki Card Generator uses advanced Large Language Models (LLMs) to turn your input into effective, memory-boosting Anki flashcards. It automatically creates translations, grammar tips, vocabulary trees, relevant images, and audio helping you learn faster, retain more, and make study sessions more engaging.

## Features

-   **Automated Card Generation:** Automatically generate Anki cards from your notes.
-   **LLM-Powered:** Uses Large Language Models to create accurate and relevant content.
-   **Image Generation:** Automatically generates and attaches images to your cards.
-   **Audio Generation:** Adds text-to-speech audio to your cards for better retention.
-   **User-Friendly GUI:** An intuitive graphical user interface to manage card generation.
-   **Customizable:** Easily configure the application to suit your needs.

## Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/your-username/anki-generator.git
    cd anki-generator
    ```

2.  **Create a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Configure the application:**

    -   Rename the `.env.example` file to `.env`.
    -   Open the `.env` file and add your API keys for the LLM and image generation services.

2.  **Run the application:**

    ```bash
    python main.py [--gui or --cli]
    ```

3.  **Use the GUI to:**

    -   Load your input data.
    -   Configure the generation settings.
    -   Start the card generation process.
    -   The generated Anki deck will be saved in the `anki_output` directory.

## Project Structure

```
. anki-generator/
├── .env # Environment variables
├── .gitignore # Git ignore file
├── README.md # Project README
├── data/ # Input data for card generation
├── logo.png # Project logo
├── main.py # Main entry point
├── requirements.txt # Project dependencies
├── src/ # Source code
│   ├── __init__.py
│   ├── app.py # Main application logic
│   ├── audio_generator.py # Audio generation module
│   ├── config.py # Configuration module
│   ├── gui.py # Graphical User Interface
│   ├── image_generator.py # Image generation module
│   ├── llm.py # Language model interaction
│   ├── processor.py # Data processing
│   └── structures.py # Data structures
└── tests/ # Tests
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue to discuss your ideas.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
 
