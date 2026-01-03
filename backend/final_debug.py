import sys
import os
import traceback

sys.path.append(os.getcwd())

try:
    from main import fetch_latest_reading
    print("Function imported. Calling it now...")
    res = fetch_latest_reading()
    print(f"Result: {res}")
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
