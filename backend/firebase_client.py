import os
from pathlib import Path
from typing import Optional
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load .env from project root
base_dir = Path(__file__).resolve().parent.parent
load_dotenv(base_dir / ".env")

_firestore_client: Optional[firestore.client] = None

def get_firestore() -> firestore.client:
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    key_name = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-key.json")
    
    # Resolve absolute path to key file
    if os.path.isabs(key_name):
        key_path = key_name
    else:
        key_path = str(base_dir / key_name)

    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'projectId': project_id,
            })
        else:
            print(f"[firebase] WARNING: Key not found at {key_path}. Falling back to default credentials.")
            # Fallback to default credentials (useful for some environments)
            firebase_admin.initialize_app(options={
                'projectId': project_id,
            })

    _firestore_client = firestore.client()
    return _firestore_client
