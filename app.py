from flask import Flask, render_template, request, redirect, url_for, session, abort
import os
import uuid
from werkzeug.utils import secure_filename
import json

# --- Imports from other modules ---
# Assuming these modules are correctly structured and accept 'api_key' now
from pdfreader import extract_text_from_pdf
from summarizer import generate_summary
from quizgenerator import create_quiz_from_text

# --- Flask App Initialization and Config ---
app = Flask(__name__)

# 1. CRITICAL: Flask must have a SECRET_KEY to use sessions.
app.secret_key = os.environ.get('SECRET_KEY', str(uuid.uuid4()))

# Define folder for temporarily storing uploads
UPLOAD_FOLDER = 'uploads'
FINAL_OUTPUT_FILE = 'output.txt' # The fixed file name for the summary

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'pdf'}

# Create the upload directory if it doesn't exist
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
FINAL_OUTPUT_FILE = os.path.join(APP_ROOT, "output.txt")
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'uploads')

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Helper function to check file extension
def allowed_file(filename):
    return '.' in filename and \
                filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---

@app.route('/')
def homepage():
    """Displays the main homepage and clears old session data for a fresh start."""
    session.pop('temp_text_path', None) 
    session.pop('gemini_api_key', None)
    return render_template('homepage.html')

@app.route('/upload', methods=['GET', 'POST'])
def pdfupload():
    """
    Handles file upload, extracts text, stores temporary file path in session, and redirects.
    """
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            return render_template('pdfupload.html', error="No file part in the request.")
        
        file = request.files['pdf_file']
        
        if file.filename == '':
            return render_template('pdfupload.html', error="No file selected.")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            pdf_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Use a unique name for the extracted text file
            temp_text_filename = f"text_{uuid.uuid4()}.txt"
            temp_text_file_path = os.path.join(app.config['UPLOAD_FOLDER'], temp_text_filename)

            try:
                # 1. Save the PDF file temporarily
                file.save(pdf_file_path)
            
                # 2. Extract text 
                extracted_text = extract_text_from_pdf(pdf_file_path)
                
                # 3. Clean up the temporary PDF file immediately
                os.remove(pdf_file_path)

                # 4. Store extracted text in a temporary file
                with open(temp_text_file_path, 'w', encoding='utf-8') as f:
                    f.write(extracted_text)

                # 5. Store the PATH (small string) in the session
                session['temp_text_path'] = temp_text_file_path
                
                # 6. Redirect to the API key entry page
                return redirect(url_for('apikey_entry'))
            
            except Exception as e:
                # Cleanup if extraction/save fails
                if os.path.exists(pdf_file_path):
                    os.remove(pdf_file_path)
                if os.path.exists(temp_text_file_path):
                    os.remove(temp_text_file_path)
                
                print(f"Error during upload/extraction: {e}")
                return render_template('pdfupload.html', error=f"Error processing file: {e}")
        else:
            return render_template('pdfupload.html', error="File type not allowed. Please upload a PDF.")

    return render_template('pdfupload.html')

@app.route('/apikey-entry', methods=['GET', 'POST'])
def apikey_entry():
    """Asks the user for the Gemini API Key, processes text from the temp file, and triggers summarization."""
    
    # CRITICAL CHECK: If temp file path isn't in the session, go back to upload.
    if 'temp_text_path' not in session:
        print("Redirecting: 'temp_text_path' not found in session. Session likely timed out or text was too large.")
        return redirect(url_for('pdfupload'))

    if request.method == 'POST':
        api_key = request.form.get('gemini_api_key')
        
        if not api_key:
            return render_template('apikey_entry.html', error="API Key is required to proceed.")
        
        # 1. Store the API Key in the session
        session['gemini_api_key'] = api_key
        
        # 2. Retrieve extracted text from temp file, then delete the file
        temp_file_path = session.pop('temp_text_path', None) # Get path and remove from session
        extracted_text = ""
        
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    extracted_text = f.read()
            finally:
                # ALWAYS delete the temporary text file
                os.remove(temp_file_path)
        
        if not extracted_text:
             # Redirect back to upload if we somehow lost the file content
            return redirect(url_for('pdfupload'))

        try:
            # 3. Generate Summary using the key and save it to FINAL_OUTPUT_FILE
            final_summary_string = generate_summary(
                extracted_text, 
                FINAL_OUTPUT_FILE,
                api_key 
            )

            # 4. Redirect to the summary page
            return redirect(url_for('summary'))
            
        except Exception as e:
            print(f"Error during summarization: {e}")
            # If summarization fails, we redirect to upload because the source text is gone.
            return render_template('apikey_entry.html', error=f"Error generating summary. Check API Key validity and try again. ({e})")

    # For GET request
    return render_template('apikey_entry.html')

@app.route('/summary')
def summary():
    """Reads the generated summary from output.txt and displays it."""
    file_content = ""

    try:
        # Read the fixed output file
        with open(FINAL_OUTPUT_FILE, 'r', encoding='utf-8') as file:
            file_content = file.read()
            
    except FileNotFoundError:
        file_content = "Error: The summary could not be found. Please upload a file first."
    except Exception as e:
        file_content = f"An error occurred while reading the summary: {e}"

    # Pass the string to the template
    return render_template('summary.html', text_from_file=file_content)

@app.route('/quiz-settings')
def quiz_settings():
    """Displays the form for the user to select quiz options."""
    # Ensure a summary exists before allowing quiz settings access
    if not os.path.exists(FINAL_OUTPUT_FILE):
        return redirect(url_for('summary')) # Redirect to summary which handles the error message
        
    return render_template('quizsetting.html')


@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    # Retrieve the API Key from the session for the quiz generation
    api_key = session.get('gemini_api_key')
    if not api_key:
         return render_template("quizpage.html", quiz_json={"error": "API Key is missing. Please restart the process from the upload page."})

    try:
        num_questions = request.form.get("num_questions", "5")
        difficulty = request.form.get("difficulty", "medium")

        with open(FINAL_OUTPUT_FILE, "r", encoding="utf-8") as f:
            summary_text = f.read().strip()

        if not summary_text:
            raise ValueError("Summary file empty — please summarize first.")

        quiz_data_dict = create_quiz_from_text(summary_text, int(num_questions), difficulty, api_key)

        return render_template(
            "quizpage.html",
            quiz_json=quiz_data_dict
        )

    except Exception as e:
        print("Error in /generate-quiz:", e)
        return render_template(
            "quizpage.html",
            quiz_json={"error": f"Quiz generation failed: {e}"}
        )


if __name__ == '__main__':

    app.run(host="0.0.0.0", port=8080)
