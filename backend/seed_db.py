import os
import sys
from pathlib import Path
import pandas as pd

sys.path.append(os.getcwd())

try:
    from firebase_client import get_firestore
    db = get_firestore()
    print("Successfully initialized Firestore.")
    
    data = {
        "ph": 7.0,
        "turbidity": 20.0,
        "temperature": 22.0,
        "do_level": 8.0,
        "timestamp": pd.Timestamp.now().isoformat()
    }
    
    print(f"Ingesting data: {data}")
    db.collection("lake_readings").add(data)
    print("SUCCESS: Data ingested.")
    
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()
