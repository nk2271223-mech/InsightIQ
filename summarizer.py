import requests
import json
import time
import os 

# --- Gemini API Configuration & Constants ---
# NOTE: API_KEY is now passed dynamically to the functions, so the global definition is removed.
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"

# Constants for Text Chunking
CHUNK_SIZE = 15000  # Max characters per chunk 
CHUNK_OVERLAP = 1000 # Overlap to maintain context between chunks

def _call_gemini_api(system_prompt, user_query, api_key):
    """
    Internal helper to handle the API call, retries, and error handling.

    Args:
        system_prompt (str): Instructions for the model's persona and task.
        user_query (str): The content or question for the model.
        api_key (str): The user-provided Gemini API key.
    """
    # Construct the API_URL dynamically using the provided api_key
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "tools": [{"google_search": {}}],
        "systemInstruction": {"parts": [{"text": system_prompt}]}
    }

    headers = { 'Content-Type': 'application/json' }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
            response.raise_for_status() 
            
            result = response.json()
            
            # Check for blockings or missing candidates
            if 'candidates' not in result or not result['candidates']:
                 # Raise an exception indicating the model failed to generate a response
                 raise Exception(f"Gemini API returned no candidates or was blocked: {result.get('promptFeedback', 'No detailed feedback.')}")

            # Extract the generated text
            summary_text = result['candidates'][0]['content']['parts'][0]['text']
            return summary_text
        
        except requests.exceptions.HTTPError as e:
            # Handle rate limiting (429) or server errors (>= 500) with exponential backoff
            if attempt < max_retries - 1 and (response.status_code == 429 or response.status_code >= 500):
                sleep_time = 2 ** attempt
                print(f"API Error ({response.status_code}). Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
            else:
                # Raise an exception for client errors (4xx) or after final retry attempt
                raise Exception(f"Failed to generate summary due to API error: {response.text}")
        except Exception as e:
            raise Exception(f"An unexpected error occurred during summary generation: {e}")
    
    raise Exception("Failed to generate summary after multiple retries.")


def chunk_text(text, max_chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Splits text into chunks with overlap for context continuity.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chunk_size, len(text))
        
        # Adjust end point to avoid splitting mid-sentence/mid-word if possible
        if end < len(text):
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            break_point = max(last_period, last_newline)
            
            # Only adjust the end point if the natural break is far enough back to include overlap
            if break_point > start + max_chunk_size - overlap:
                end = break_point + 1
            
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        # Set the next start point, using overlap for context
        start = end - overlap if end < len(text) else len(text)
        
    return chunks


def generate_summary(text_to_summarize: str, output_filepath: str, api_key: str) -> str:
    """
    Performs two-stage summarization (chunking + final summary) and returns the summary string.
    CRITICALLY: It also saves the summary to the output_filepath for later use by the quiz generator.

    Args:
        text_to_summarize (str): The string content extracted from the PDF.
        output_filepath (str): The path where the final summary must be saved (e.g., "output.txt").
        api_key (str): The user-provided Gemini API key. # <<< NEW PARAMETER

    Returns:
        str: The final, generated summary string.
    """
    # Input validation
    if not api_key:
        raise ValueError("Gemini API Key is required for summarization.")
    
    try:
        # Check if chunking is necessary
        if len(text_to_summarize) > CHUNK_SIZE:
            print(f"Document size ({len(text_to_summarize)} chars) requires chunking and two-stage summarization.")
            
            # --- STAGE 1: SEGMENT SUMMARIES ---
            chunks = chunk_text(text_to_summarize)
            segment_summaries = []
            segment_system_prompt = (
                "You are a segment summarizer. Read the following text chunk from a large document. "
                "Generate a detailed, stand-alone summary for this chunk, retaining all key concepts. "
                "The summary must be precise and objective. Do not introduce yourself."
            )
            
            for i, chunk in enumerate(chunks):
                print(f"Generating summary for chunk {i+1}/{len(chunks)}...")
                segment_user_query = f"Summarize this segment:\n\n---\n\n{chunk}"
                
                # PASS THE API KEY to the helper function
                segment_summary = _call_gemini_api(segment_system_prompt, segment_user_query, api_key)
                segment_summaries.append(segment_summary)
            
            # Combine all segment summaries for the final stage
            combined_summary_text = "\n\n---\n\n".join(segment_summaries)
            final_input_text = combined_summary_text
            
        else:
            # If the text is small enough, skip chunking and go straight to final stage
            final_input_text = text_to_summarize
            
        # --- STAGE 2: FINAL SUMMARY ---
        final_system_prompt = (
            "You are an expert academic assistant. Analyze the provided text from the document "
            "and generate a comprehensive, clear, and professional summary suitable for study or analysis. "
            "The summary must be approximately 300 words and focus on key arguments, findings, and conclusions. "
            "Format the summary as continuous, readable paragraphs."
        )
        
        # PASS THE API KEY to the helper function
        summary_result = _call_gemini_api(final_system_prompt, final_input_text, api_key)
        
        # --- CRITICAL STEP: Write the summary string to the specified file path ---
        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(summary_result)
                
        except Exception as file_error:
            # If saving fails, raise an exception so the upload route catches it
            raise IOError(f"Failed to save summary to {output_filepath}: {file_error}")
            
        # Return the summary string
        return summary_result
        
    except Exception as e:
        # Re-raise the exception to be handled by the Flask app
        raise e