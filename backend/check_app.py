import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

try:
    print("Importing main...")
    import main
    print("Import successful.")
    print(f"App initialized: {main.app}")
except Exception as e:
    print(f"FAILED to initialize app: {e}")
    import traceback
    traceback.print_exc()
