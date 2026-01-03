import os
from google import genai
from dotenv import load_dotenv
from pathlib import Path

# Load env
base_dir = Path(__file__).resolve().parent.parent
load_dotenv(base_dir / ".env")

def debug_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    system_prompt = (
        "You are 'SLIM AI Senior Ecology Specialist'. Provide a highly concise, data-driven analysis.\n\n"
        "STRICT STRUCTURE:\n"
        "1. CONCLUSION: [Single bold sentence identifying the status/suitability]\n"
        "2. SCIENTIFIC REASONING: [3-4 short bullet points explaining the 'why' based on current data trends.]\n\n"
        "Rules: No introductions. No fluff. Be direct and technical."
    )
    
    data = "pH: 7.2, Turbidity: 25.0, Temp: 24.0, DO: 7.8"
    question = "is the lake suitable for irrigation"
    prompt = f"{system_prompt}\n\nDATA:\n{data}\n\nQUESTION: {question}"
    
    model_id = "gemini-2.5-flash-preview-09-2025"
    
    print(f"\n--- Testing Model: {model_id} ---")
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config={
                "max_output_tokens": 400,
                "temperature": 0.2,
                "safety_settings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                ]
            }
        )
        print(f"Response text length: {len(response.text) if response.text else 'None'}")
        if response.text:
            print("Response Content:")
            print(response.text)
        else:
            print(f"Finish Reason: {response.candidates[0].finish_reason if response.candidates else 'No candidates'}")
    except Exception as e:
        print(f"Error for {model_id}: {e}")

if __name__ == "__main__":
    debug_gemini()
