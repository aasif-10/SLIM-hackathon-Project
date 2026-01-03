import sys
import os
import traceback
from pathlib import Path

# Add backend to path
sys.path.append(os.getcwd())

def test_research():
    try:
        print("Importing research_models...")
        from research_models import compute_research_models
        print("Calling compute_research_models()...")
        res = compute_research_models()
        print("Success!")
        print(f"Result nodes count: {len(res.gnn.nodes)}")
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test_research()
