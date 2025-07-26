# Arabic Voice Assistant (Backend)

This is a backend Flask app for an Arabic voice assistant that supports dialect-specific Arabic coding explanations using LLMs (like GPT-4) and voice transcription.

🛠 Setup Instructions

1. Clone the repository:
   git clone https://github.com/your-username/arabic-voice-assistant-backend.git
   cd arabic-voice-assistant-backend

2. Create a virtual environment:
   python3 -m venv venv
   source venv/bin/activate   # On Windows use `venv\Scripts\activate`

3. Install dependencies:
   pip install -r requirements.txt

4. Add your environment variables:
   cp .env.example .env
   # Then edit .env with your actual OpenAI API key

5. Run the server:
   flask run
   # Or: python app.py

🎙 How It Works

- Accepts POST requests to /ask with text, audio, and dialect
- (TODO) Transcribes audio to Arabic text via Whisper API
- (TODO) Builds GPT prompt based on selected dialect
- (TODO) Returns Arabic response and code

🧪 Sample Request (via curl or Postman)

curl -X POST http://127.0.0.1:5000/ask \
  -F "text=اشرح لي كيف أنشئ دالة بايثون" \
  -F "dialect=Egyptian"
