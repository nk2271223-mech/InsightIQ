🧠 InsightIQ
Overview
InsightIQ is a Flask-based web application that leverages advanced language models (e.g., OpenAI, Google Gemini, or a similar API) to automatically process a user-uploaded PDF document. It provides a concise summary of the document's content and generates a custom multiple-choice quiz based on the key information.

This tool is perfect for students, professionals, and anyone who needs to quickly digest information and test their understanding of complex documents.

✨ Features
PDF Upload: Seamlessly upload a .pdf file via a clean, user-friendly interface.

Intelligent Summarization: Utilizes AI to generate a concise, accurate summary of the entire document.

Automatic Quiz Generation: Creates a set of multiple-choice questions based on the summary and key concepts within the PDF.

Flask Backend: Robust and scalable backend built with Python and the Flask framework.

Error Handling: Provides clear feedback to the user on upload failures (e.g., incorrect file type, API issues).

🛠️ Installation and Setup
Prerequisites
You need Python 3.8+ installed on your system.

Steps
Clone the Repository:

Bash

git clone [Your-Repository-URL]
cd ai-pdf-summarizer-quiz-maker
Create a Virtual Environment:

Bash

python -m venv venv
source venv/bin/activate  # On Linux/macOS
# venv\Scripts\activate   # On Windows
Install Dependencies: You'll need a requirements.txt file listing packages like Flask, gunicorn, pypdf or pdfplumber (for PDF parsing), and the chosen AI SDK (openai, google-genai, etc.).

Bash

pip install -r requirements.txt
Configure API Key: The application requires an AI API key. Create a file named .env in the root directory and add your key.

Note: The exact variable name depends on your chosen AI service (e.g., OPENAI_API_KEY, GEMINI_API_KEY).

# Example for OpenAI
OPENAI_API_KEY="your_api_key_here"

# Example for Google Gemini
GEMINI_API_KEY="your_api_key_here"
🚀 Usage
1. Run the Application
Start the Flask development server:

Bash

flask run
# The server will usually run on: http://127.0.0.1:5000/
2. Upload and Process
Open your web browser and navigate to the application URL (e.g., http://127.0.0.1:5000/).

Click the "Choose PDF File" button and select a .pdf document.

Click the "Upload & Summarize" button.

The application will process the file, extract the text, send it to the AI model, and then display the summary and quiz results on the next page.

⚙️ Technology Stack
Backend: Python, Flask

File Handling: werkzeug (part of Flask)

PDF Parsing: pypdf or pdfplumber

Artificial Intelligence: [Specify which AI SDK/API you are using, e.g., OpenAI Python SDK or Google GenAI SDK]

Frontend: HTML5, CSS3, JavaScript (Jinja2 templating for dynamic data)

🤝 Contributing
Contributions are welcome! If you have suggestions for improvements, please feel free to fork the repository and submit a pull request.

📝 License
This project is licensed under the MIT License - see the LICENSE file for details.
