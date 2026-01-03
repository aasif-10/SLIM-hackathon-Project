import os
from pathlib import Path
import sys

# Add backend to path so we can import firebase_client
sys.path.append(os.getcwd())

try:
    from firebase_client import get_firestore
    db = get_firestore()
    print("Successfully initialized Firestore.")
    
    docs = db.collection("lake_readings").limit(5).stream()
    count = 0
    for doc in docs:
        print(f"Doc ID: {doc.id}, Data: {doc.to_dict()}")
        count += 1
    
    if count == 0:
        print("Collection 'lake_readings' is EMPTY.")
    else:
        print(f"Found {count} documents in 'lake_readings'.")
        
except Exception as e:
    import traceback
    print(f"Error connecting to Firebase: {e}")
    traceback.print_exc()
