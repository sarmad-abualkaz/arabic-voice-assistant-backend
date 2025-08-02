from flask import Flask, request, jsonify
from faster_whisper import WhisperModel
import json
from flask import Response



import os
import requests
import openai

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

USE_LOCAL_MODELS = os.getenv("USE_LOCAL_MODELS", "false").lower() == "true"
openai.api_key = os.getenv("OPENAI_API_KEY")

# Define a dialect map for prompt construction
DIALECT_MAP = {
    "MSA": "باللغة العربية الفصحى",
    "Egyptian": "باللهجة المصرية",
    "Gulf": "باللهجة الخليجية",
    "Levantine": "باللهجة الشامية",
    "Iraqi": "باللهجة العراقية",
    "Tunisian": "باللهجة التونسية",
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

model = WhisperModel("medium")

def build_prompt(dialect: str, user_question: str) -> str:
    # Use the selected dialect to build a natural prompt for GPT
    # Add any formatting, examples or context needed for your prompt format
    dialect_phrase = DIALECT_MAP.get(dialect, "باللغة العربية")
    return f"اشرح للمستخدم {dialect_phrase}: {user_question}"

def transcribe_audio_local(audio_path):
    # Use faster-whisper model to transcribe audio locally
    # Developer should:
    # - Load a local Whisper-compatible model (e.g., faster-whisper)
    # - Run transcription on the audio_path
    # - Return the transcribed text
    segments, info = model.transcribe(audio_path)

    # Combine all segments into one string
    text = " ".join(segment.text for segment in segments)
    return text


def transcribe_audio_remote(audio_path):
    # Use OpenAI Whisper API to transcribe audio remotely
    # Developer should:
    # - Upload the file to OpenAI's endpoint
    # - Handle API key and headers securely
    # - Parse the response and extract transcript
    # - Return the transcribed text
    with open(audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

def generate_response_local(prompt):
    # Generate a response using a local LLM (e.g. Ollama running locally)
    # Developer should:
    # - Send the prompt to the local model endpoint (e.g. http://localhost:11434)
    # - Handle JSON formatting
    # - Return the response text from the model
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
    # Generate a response using OpenAI GPT (e.g. GPT-4)
    # Developer should:
    # - Send the prompt to OpenAI's API with necessary headers
    # - Handle error cases
    # - Return the response text from the model
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # Or "gpt-4" if you want
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message["content"]

@app.route("/ask", methods=["POST"])
def ask():
    try:
        # Step 1: Retrieve the input fields from the incoming POST request
        user_text = request.form.get("text")
        dialect = request.form.get("dialect", "MSA")
        audio_file = request.files.get("audio")

        transcript = None

        # Step 2: If audio is provided:
        if audio_file:
            # Validate audio file
            if not audio_file.filename:
                return jsonify({"error": "Invalid audio file"}), 400
                            
            temp_audio_path = "temp.wav"
                        
            try:
                audio_file.save(temp_audio_path)

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
                # Step 6 (Final Step): Return JSON response (include transcript only if audio was used)
        result = {"response": response_text.strip()}
        if transcript:
            result["transcript"] = transcript.strip()

        return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json"), 200

    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
