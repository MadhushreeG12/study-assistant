# How to Run the Project

## Prerequisites

Before running the application, ensure you have the following installed:

1.  **Python 3.x**: [Download Python](https://www.python.org/downloads/)
2.  **Tesseract-OCR**: Required for OCR functionality.
    *   **Windows**: [Download Installer](https://github.com/UB-Mannheim/tesseract/wiki)
    *   Add the installation path (e.g., `C:\Program Files\Tesseract-OCR`) to your system PATH.
3.  **Poppler**: Required for PDF to image conversion.
    *   **Windows**: [Download Binary](https://github.com/oschwartz10612/poppler-windows/releases/)
    *   Extract the archive and add the `bin` folder to your system PATH.

## Setup

1.  Open a terminal (Command Prompt or PowerShell).
2.  Navigate to the project directory:
    ```bash
    cd "c:/Users/Manoj G/Downloads/updated_ai/updated_ai"
    ```
3.  Install the Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

The application uses the Groq API for summarization. A default key is provided in the code, but for production or heavy use, you should set your own environment variable:

*   **Windows (PowerShell)**:
    ```powershell
    $env:GROQ_API_KEY = "your_api_key_here"
    ```
*   **Windows (CMD)**:
    ```cmd
    set GROQ_API_KEY=your_api_key_here
    ```

## Running the Application

1.  Run the `main.py` script:
    ```bash
    python main.py
    ```
2.  Open your web browser and go to:
    [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Usage

1.  **Login**: Use the login page to access the application.
2.  **Upload**: Upload PDF files or Video files (MP4) for summarization.
3.  **YouTube**: Paste a YouTube URL to summarize the video content.
4.  **History**: View your past summaries.
