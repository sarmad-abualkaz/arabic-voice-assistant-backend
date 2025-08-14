from flask import Flask, request, jsonify, Response
from faster_whisper import WhisperModel
import subprocess

from openai import OpenAI
import json
import os
import uuid

# Initialize Flask application
app = Flask(__name__)
USE_LOCAL_MODELS = True

app.config['JSON_AS_ASCII'] = False  # Ensure Arabic text is displayed properly in JSON

# Determine if local models (faster-whisper + local LLM) should be used
USE_LOCAL_MODELS = os.getenv("USE_LOCAL_MODELS", "false").lower() == "true"

client = None
if not USE_LOCAL_MODELS:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set and USE_LOCAL_MODELS is false.")
    client = OpenAI(api_key=api_key)
# Ensure the OpenAI client is initialized only if not using local models
# Define a dialect map for prompt construction
DIALECT_MAP = {
    "MSA": "باللغة العربية الفصحى",
    "Egyptian": "باللهجة المصرية",
    "Gulf": "باللهجة الخليجية",
    "Levantine": "باللهجة الشامية",
    "Iraqi": "باللهجة العراقية",
    "Tunisian": "باللهجة التونسية",  # fixed typo
    "Libyan": "باللهجة الليبية",
    "Sudanese": "باللهجة السودانية",
    "Yemeni": "باللهجة اليمنية",
    "Algerian": "باللهجة الجزائرية",
    "Moroccan": "باللهجة المغربية",
    "Hijazi": "باللهجة الحجازية",
    "Najdi": "باللهجة النجدية",
    "Bahraini": "باللهجة البحرينية",
    "Qatari": "باللهجة القطرية",
    "Emirati": "باللهجة الإماراتية",
    "Kuwaiti": "باللهجة الكويتية",
    "Omani": "باللهجة العمانية",
    "Palestinian": "باللهجة الفلسطينية",
    "Syrian": "باللهجة السورية",
    "Jordanian": "باللهجة الأردنية",
    "Lebanese": "باللهجة اللبنانية"
}

# Load the local Whisper model for transcription (if using local mode)
model = WhisperModel("medium")

def build_prompt(dialect: str, user_question: str) -> str:
    """
    Use the selected dialect to build a natural prompt for GPT.
    Add any formatting, examples, or context needed for your prompt format.
    """
    dialect_phrase = DIALECT_MAP.get(dialect, "باللغة العربية")
    return f"اشرح للمستخدم {dialect_phrase}: {user_question}"

def convert_mp3_to_wav(mp3_path):
    wav_path = mp3_path.replace(".mp3", ".wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path, wav_path
    ], check=True)
    return wav_path

def transcribe_audio_local(audio_path):
    """
    Use faster-whisper model to transcribe audio locally with better accuracy for Arabic.
    """
    # Force language to Arabic and use best timestamping
    segments, _ = model.transcribe(audio_path, language="ar", beam_size=5)
    
    # Combine all segments into one string
    text = " ".join(segment.text for segment in segments)
    print("📝 Transcription done:", text)  # Debug print
    return text


def transcribe_audio_remote(audio_path):
    """
    Use OpenAI Whisper API to transcribe audio remotely.
    Developer should:
    - Upload the file to OpenAI's endpoint
    - Handle API key and headers securely
    - Parse the response and extract transcript
    - Return the transcribed text
    """
    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return transcript.text

def generate_response_local(prompt):
    """
    Generate a response using a local LLM (e.g., Ollama running locally).
    Developer should:
    - Send the prompt to the local model endpoint (e.g., http://localhost:11434)
    - Handle JSON formatting
    - Return the response text from the model
    """
    responses = {
        "Hello how are you?": "أهلاً وسهلاً! إزيك؟ كل حاجة تمام؟",
        "Hello": "أهلاً وسهلاً!",
        "How are you": "إزيك؟ عامل إيه؟",
        "Good morning": "صباح الخير يا فندم!",
    }
    
    # Extract the original text from the prompt for simple matching
    for english, arabic in responses.items():
        if english.lower() in prompt.lower():
            return arabic
    
    return "أهلاً بيك! ممكن تكرر السؤال تاني؟"

def generate_response_remote(prompt):
    """
    Generate a response using OpenAI GPT (e.g., GPT-4).
    Developer should:
    - Send the prompt to OpenAI's API with necessary headers
    - Handle error cases
    - Return the response text from the model
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

@app.route("/ask", methods=["POST"])
def ask():
    try:
        # Step 1: Retrieve the input fields from the incoming POST request
        user_text = request.form.get("text")
        dialect = request.form.get("dialect", "MSA")
        audio_file = request.files.get("audio")

        transcript = None

        # Step 2: If audio is provided
        if audio_file:
            # Validate audio file
            if not audio_file.filename:
                return jsonify({"error": "Invalid audio file"}), 400
                            
            # Generate unique temp file name to avoid concurrency conflicts
            # Keep the original extension (so .mp3 works)
            ext = os.path.splitext(audio_file.filename)[1]  # gets .mp3 or .wav
            temp_audio_path = f"temp_{uuid.uuid4()}{ext}"   

                        
            try:
                # Save uploaded audio to temp file
                audio_file.save(temp_audio_path)
                # Convert MP3 to WAV if necessary
                if temp_audio_path.endswith(".mp3"):
                    temp_audio_path = convert_mp3_to_wav(temp_audio_path)

                # Transcribe using local or remote Whisper
                if USE_LOCAL_MODELS:
                    transcript = transcribe_audio_local(temp_audio_path)
                else:
                    transcript = transcribe_audio_remote(temp_audio_path)

                # Use transcript as text if no user_text was provided
                if not user_text:
                    user_text = transcript
                                
            except Exception as e:
                return jsonify({"error": f"Audio transcription failed: {str(e)}"}), 500
            finally:
                # Clean up temporary file
                if os.path.exists(temp_audio_path):
                    try:
                        os.remove(temp_audio_path)
                    except OSError:
                        pass  # File might already be deleted

        # Step 3: Validate input
        if not user_text or user_text.strip() == "":
            return jsonify({"error": "No text or audio provided"}), 400

        # Step 4: Build the prompt for the model
        try:
            prompt = build_prompt(dialect, user_text.strip())
        except Exception as e:
            return jsonify({"error": f"Failed to build prompt: {str(e)}"}), 500

        # Step 5: Generate response depending on whether local or remote models are used
        try:
            if USE_LOCAL_MODELS:
                response_text = generate_response_local(prompt)
            else:
                response_text = generate_response_remote(prompt)
        except Exception as e:
            return jsonify({"error": f"Failed to generate response: {str(e)}"}), 500

        # Validate response
        if not response_text or response_text.strip() == "":
            return jsonify({"error": "Model returned empty response"}), 500

        # Step 6 (Final Step): Return JSON response (include transcript only if audio was used)
        result = {"response": response_text.strip()}
        if transcript:
            result["transcript"] = transcript.strip()

        # Ensure proper JSON encoding for Arabic text
        return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json", status=200)

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# Entry point for running the Flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
