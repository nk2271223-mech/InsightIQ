import requests
import json
import time
import os
from typing import Dict, Any

# --- Configuration & Constants ---
# NOTE: API_KEY is now handled dynamically through function arguments.
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
FINAL_OUTPUT_FILE = "output.txt" 
QUIZ_FILE_NAME = FINAL_OUTPUT_FILE # Keeping QUIZ_FILE_NAME for compatibility

# --- Helper Functions for Gemini API Structured Call ---

def _call_gemini_api_structured(user_query: str, schema: Dict[str, Any], system_prompt: str, api_key: str) -> Dict[str, Any]:
    """
    Internal helper to handle the API call, retries, and return structured JSON.

    Args:
        user_query (str): The content or question for the model.
        schema (Dict[str, Any]): The JSON schema for the desired structured output.
        system_prompt (str): Instructions for the model's persona and task.
        api_key (str): The user-provided Gemini API key. # <<< NEW PARAMETER
    """
    # Construct the API_URL dynamically using the provided api_key
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }

    headers = { 'Content-Type': 'application/json' }
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Set a timeout for the API call
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=60)
            response.raise_for_status() 
            
            result = response.json()
            
            # The structured JSON response is returned as a string in the 'text' part
            if (result.get('candidates') and 
                result['candidates'][0].get('content') and 
                result['candidates'][0]['content'].get('parts')):

                # Safely extract the Gemini model’s text output
                json_string = result['candidates'][0]['content']['parts'][0].get('text', '{}').strip()
                print("\n=== RAW GEMINI QUIZ OUTPUT ===\n", json_string[:500], "...\n")  # optional debug

                try:
                    parsed = json.loads(json_string)

                    # ✅ Ensure structure consistency so frontend can read it
                    if not isinstance(parsed, dict):
                        parsed = {"questions": []}
                    if "questions" not in parsed:
                        parsed = {"questions": []}

                    return parsed

                except json.JSONDecodeError:
                    print("⚠️ Gemini returned malformed JSON:", json_string)
                    return {"questions": []}
            else:
                # Check for prompt feedback if candidates are missing (e.g., safety blocking)
                feedback = result.get('promptFeedback', {}).get('blockReason', 'Unknown reason')
                raise Exception(f"API returned an invalid or empty response structure. Blocking reason: {feedback}")

        except requests.exceptions.HTTPError as e:
            if attempt < max_retries - 1 and (response.status_code == 429 or response.status_code >= 500):
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
            else:
                raise Exception(f"Failed to generate quiz due to API error: {response.text}")
        except Exception as e:
            # Check for non-JSON response structure which is a common error
            if "json" not in str(e).lower():
                print("Warning: Non-JSON response received. Check model output structure.")
            raise Exception(f"An unexpected error occurred during API call: {e}")
    
    raise Exception("Failed to generate quiz after multiple retries.")


def create_quiz_from_text(source_content: str, num_questions: int, difficulty: str, api_key: str) -> Dict[str, Any]:
    """
    Generates a structured quiz using the Gemini API based on source content and settings.

    Args:
        source_content (str): The summary or extracted text to base the quiz on.
        num_questions (int): The required number of questions.
        difficulty (str): The desired difficulty level.
        api_key (str): The user-provided Gemini API key. # <<< NEW PARAMETER
    """
    
    if not source_content.strip():
        raise ValueError("Source content for quiz generation is empty.")

    if not api_key:
        raise ValueError("Gemini API Key is required for quiz generation.")

    print(f"Generating {num_questions} {difficulty} quiz...")
    
    # --- 1. Define Quiz JSON Schema ---
    quiz_schema = {
        "type": "OBJECT",
        "properties": {
            "questions": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "questionNumber": {"type": "INTEGER"},
                        "question": {"type": "STRING"},
                        "imageUrl": {"type": "STRING"},
                        "answerOptions": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "text": {"type": "STRING"},
                                    "rationale": {"type": "STRING"},
                                    "isCorrect": {"type": "BOOLEAN"}
                                }
                            }
                        },
                        "hint": {"type": "STRING"}
                    },
                    "propertyOrdering": ["questionNumber", "question", "imageUrl", "answerOptions", "hint"]
                }
            }
        },
        "propertyOrdering": ["questions"]
    }
    
    # --- 2. Define Prompts (Dynamically generated) ---
    system_prompt = (
        f"You are a test generator. Your task is to create exactly **{num_questions}** multiple-choice questions (MCQs) "
        "with 4 options each, based *only* on the content provided by the user. "
        f"The difficulty level for these questions must be **{difficulty}**. "
        "Ensure the questions cover key facts, concepts, and conclusions from the text. "
        "For each question, provide a detailed rationale for every option and set exactly one option as correct. "
        "The questions should test comprehension and critical thinking, not just simple recall. "
        "Set the 'imageUrl' property to an empty string. The output MUST strictly follow the provided JSON schema."
    )
    
    user_query = f"Generate a quiz based on the following text:\n\n---\n\n{source_content}"
    
    # --- 3. Call API and return result ---
    # PASS THE API KEY to the structured helper function
    quiz_data = _call_gemini_api_structured(user_query, quiz_schema, system_prompt, api_key)
    
    # Ensure question numbers are sequentially correct
    for i, q in enumerate(quiz_data.get('questions', [])):
        q['questionNumber'] = i + 1
    print("DEBUG QUIZ DATA:", json.dumps(quiz_data, indent=2))
    
    return quiz_data