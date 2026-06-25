import os
from dotenv import load_dotenv

try:
    from google import genai  # type: ignore
except Exception:
    genai = None

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

if not api_key or genai is None:
    print("No API key found")
else:
    try:
        print("Available models:")
        client = genai.Client(api_key=api_key)
        for m in client.models.list():
            print(m.name)
    except Exception as e:
        print(f"Error listing models: {e}")
