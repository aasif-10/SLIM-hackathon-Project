import os
import sys
import traceback
from pathlib import Path

# Mock FastAPI state if needed, but here we just want the logic
sys.path.append(os.getcwd())

def test_latest_logic():
    try:
        from main import fetch_latest_reading
        print("Calling fetch_latest_reading()...")
        result = fetch_latest_reading()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Caught exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_latest_logic()
