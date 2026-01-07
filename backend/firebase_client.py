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
        # 1. Try Environment Variable (Production/Render)
        firebase_json_content = os.getenv("FIREBASE_KEY_JSON")
        if firebase_json_content:
            try:
                import json
                # Handle potential quoting issues if pasted as string
                if isinstance(firebase_json_content, str):
                    try:
                        cred_dict = json.loads(firebase_json_content)
                    except json.JSONDecodeError:
                        print("[firebase] Error decoding FIREBASE_KEY_JSON env var")
                        cred_dict = None
                
                if cred_dict:
                    cred = credentials.Certificate(cred_dict)
                    firebase_admin.initialize_app(cred, {'projectId': project_id})
                    print("[firebase] Initialized via FIREBASE_KEY_JSON env var")
            except Exception as e:
                print(f"[firebase] Failed to init from env var: {e}")

        # 2. Try File Path (Development)
        elif os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'projectId': project_id,
            })
            print(f"[firebase] Initialized via file: {key_path}")
            
        else:
            print(f"[firebase] WARNING: Key not found at {key_path} and no Env Var. Authenticating with default credentials.")
            # Fallback to default credentials (useful for some environments)
            firebase_admin.initialize_app(options={
                'projectId': project_id,
            })

    try:
        if not firebase_admin._apps:
             # Logic will be skipped if already initialized
             _firestore_client = firestore.client()
        else:
             _firestore_client = firestore.client()
    except Exception as e:
        print(f"[firebase] CRITICAL: Failed to create Firestore client even after init logic. Error: {e}")
        return None

    return _firestore_client
