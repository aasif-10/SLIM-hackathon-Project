import os
import sys
from pathlib import Path
import pandas as pd

sys.path.append(os.getcwd())

try:
    from firebase_client import get_firestore
    db = get_firestore()
    print("Successfully initialized Firestore.")
    
    print("Running query: db.collection('lake_readings').order_by('timestamp', direction='DESCENDING').limit(1).stream()")
    docs = (
        db.collection("lake_readings")
        .order_by("timestamp", direction="DESCENDING")
        .limit(1)
        .stream()
    )
    
    data = [doc.to_dict() for doc in docs]
    print(f"Data retrieved: {data}")
    
except Exception as e:
    import traceback
    print(f"Error executing query: {e}")
    traceback.print_exc()
