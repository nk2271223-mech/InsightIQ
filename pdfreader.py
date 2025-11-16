import fitz # PyMuPDF

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Reads the text from a PDF file and returns the content as a single string 
    named 'text'. This function does NOT save to a file.

    Args:
        pdf_path (str): The temporary path where the uploaded PDF is stored.

    Returns:
        str: A single string containing all the extracted PDF text.
    """
    
    # 1. Initialize the final string variable 'text'
    text = ""
    
    try:
        # Open the PDF document using PyMuPDF (fitz)
        with fitz.open(pdf_path) as doc:
            
            # Loop through all pages and extract the text
            all_page_texts = [page.get_text() for page in doc]
            
            # 2. Concatenate all page texts into the single string 'text'
            text = "\n\n".join(all_page_texts)
            
            # 3. Return the string immediately
            return text
            
    except fitz.FileNotFoundError:
        # This error should be rare since the Flask app checks existence, but included for robustness.
        return f"Error: PDF file not found at path: {pdf_path}"
        
    except Exception as e:
        # Handle other potential errors during processing
        return f"Error extracting text from PDF: {e}"

# NOTE: The function name has been changed to 'extract_text_from_pdf' to reflect its new purpose.