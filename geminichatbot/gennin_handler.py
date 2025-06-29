import os
import time
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv("api.env")
API_KEY = os.getenv("GENIUS_API_KEY")  # Make sure this matches your .env file

if not API_KEY:
    raise ValueError("API key not found!")

# Configure the API
genai.configure(api_key=API_KEY)

# Initialize the model - using latest recommended version
model = genai.GenerativeModel("gemini-2.0-flash")  # Updated model name

# Rate limiting variables
LAST_CALL_TIME = 0
MIN_INTERVAL = 1  # 1 second between calls

def ask_gemini(prompt):
    global LAST_CALL_TIME
    
    try:
        # Enforce rate limiting
        elapsed = time.time() - LAST_CALL_TIME
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        
        # Generate content
        response = model.generate_content(prompt)
        LAST_CALL_TIME = time.time()
        
        # Return the text response
        return response.text
    
    except Exception as e:
        if "quota" in str(e).lower():
            print("Rate limit exceeded - waiting 20 seconds")
            time.sleep(20)
            return ask_gemini(prompt)  # Retry
        return f"Error: {str(e)}"

# Debug information
print("All imports working correctly!")
print(f"Current directory: {os.getcwd()}")
print(f"Files present: {os.listdir()}")

# Test the function
test_response = ask_gemini("Hello in 5 languages:")
print("Gemini Response:", test_response)