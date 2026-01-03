from pathlib import Path
import traceback
from google import genai
from dotenv import load_dotenv
import os

# Load .env from project root
base_dir = Path(__file__).resolve().parent.parent
load_dotenv(base_dir / ".env")

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def generate_narrative(prompt: str, max_tokens: int = 150) -> str:
    """Helper to generate a short narrative from Gemini."""
    client = get_gemini_client()
    if not client:
        return "Gemini API key not configured."
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-09-2025",
            contents=prompt,
            config={
                "max_output_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        return response.text if response.text else "No response from AI."
    except Exception:
        print(f"[ai_utils] Error: {traceback.format_exc()}")
        return "AI analysis unavailable (check logs)."
