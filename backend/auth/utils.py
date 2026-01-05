import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import requests
from fastapi import HTTPException, status
from dotenv import load_dotenv
from pathlib import Path

# Load env vars
base_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(base_dir / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_change_in_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_google_token(id_token: str) -> Dict[str, Any]:
    """
    Verifies the Google ID token. 
    In a production env, you should verify the signature against Google's public keys.
    For simplicity here, we can use the tokeninfo endpoint or a library like google-auth.
    Here we use the tokeninfo endpoint for ease of implementation without extra heavy deps,
    but checking audience is critical.
    """
    try:
        # verify via google's tokeninfo endpoint
        response = requests.get(f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}")
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google Token")
        
        token_info = response.json()
        
        # Verify Audience
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        if google_client_id and token_info.get("aud") != google_client_id:
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token audience mismatch")
             
        return token_info
    except Exception as e:
        print(f"Google Token Verification Error: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not verify Google Token")
