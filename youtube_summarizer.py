from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import os
import textwrap
from collections import deque

app = Flask(__name__)
CORS(app)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBmHpu1I6Xv-FCBn0-e4eovJ93wAmV7i4c')
genai.configure(api_key=GEMINI_API_KEY)

# Improved model configuration
generation_config = {
    "temperature": 0.2,  # More factual responses
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 300,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",  # Use latest model
    generation_config=generation_config,
    safety_settings=safety_settings
)

def extract_video_id(url):
    """Improved URL parsing with more patterns"""
    patterns = [
        r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})",
        r"youtube\.com\/shorts\/([^\"&?\/\s]{11})",
        r"youtube\.com\/live\/([^\"&?\/\s]{11})",
        r"youtube\.com\/watch\?v=([^\"&?\/\s]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_transcript(video_id, max_retries=3):
    """Fetch transcript with retry logic"""
    for attempt in range(max_retries):
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([entry['text'] for entry in transcript])
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Final transcript error: {str(e)}")
                return None
            continue
    return None

def chunk_text(text, max_length=15000):
    """Break long text into chunks that fit Gemini's context window"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_length:
            current_chunk.append(word)
            current_length += len(word) + 1
        else:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def summarize_with_gemini(text, max_retries=2):
    """Improved summarization with chunking and retry logic"""
    chunks = chunk_text(text)
    summaries = []
    
    for chunk in chunks:
        for attempt in range(max_retries):
            try:
                prompt = textwrap.dedent(f"""
                Create a detailed yet concise summary of the following YouTube video transcript.
                Focus on key facts, main arguments, and important details.
                Use bullet points if appropriate.
                Be completely factual and avoid any interpretation or commentary.

                Transcript:
                {chunk}

                Summary:
                """)
                
                response = model.generate_content(prompt)
                if response.text:
                    summaries.append(response.text)
                    break
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Final Gemini error on chunk: {str(e)}")
                    return None
                continue
    
    if not summaries:
        return None
    
    # Combine chunk summaries if needed
    if len(summaries) > 1:
        combined = "\n".join(summaries)
        try:
            response = model.generate_content(f"Combine these summaries into one cohesive summary:\n{combined}")
            return response.text
        except:
            return "\n\n".join(summaries)
    return summaries[0]

def basic_text_summarizer(text, max_sentences=5):
    """Simple extractive summarizer as final fallback"""
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
    important_sentences = deque(maxlen=max_sentences)
    
    # Simple heuristic: longer sentences often contain more information
    for sentence in sentences:
        if len(sentence.split()) > 10:  # Only consider reasonably long sentences
            if not important_sentences or len(sentence) > len(important_sentences[0]):
                important_sentences.appendleft(sentence)
    
    return " ".join(important_sentences) if important_sentences else text[:500] + "..."

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({"error": "YouTube URL is required"}), 400
    
    video_id = extract_video_id(data['url'])
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    transcript = get_transcript(video_id)
    if not transcript:
        return jsonify({"error": "Transcript not available"}), 404
    
    # Try Gemini first
    summary = summarize_with_gemini(transcript)
    
    # If Gemini fails, try basic summarizer
    if not summary:
        summary = basic_text_summarizer(transcript)
        return jsonify({
            "video_id": video_id,
            "summary": summary,
            "transcript_length": len(transcript),
            "model": "basic-text-summarizer",
            "warning": "Gemini summarization failed, using basic summary"
        })
    
    return jsonify({
        "video_id": video_id,
        "summary": summary,
        "transcript_length": len(transcript),
        "model": "gemini-1.5-pro"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)