from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse, JSONResponse
import requests
import os
from typing import Optional
from auth.utils import create_access_token, verify_google_token, ACCESS_TOKEN_EXPIRE_MINUTES
from auth.models import User, Token
from auth.dependencies import get_current_user
from firebase_client import get_firestore
from datetime import datetime, timedelta
from urllib.parse import urlencode

router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={404: {"description": "Not found"}},
)

# Configuration keys
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
REDIRECT_URI = f"{BASE_URL}/auth/callback"

@router.get("/login")
def login(request: Request):
    """
    Redirects the user to the Google OAuth 2.0 consent screen.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID not configured")
    
    scope = "openid email profile"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": REDIRECT_URI,
        "access_type": "offline",
        "include_granted_scopes": "true",
    }
    
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(auth_url)

@router.get("/callback")
def auth_callback(code: str, error: Optional[str] = None):
    """
    Exchanges the authorization code for tokens, verifies state, 
    upserts user, and returns access token (via redirect or JSON).
    """
    if error:
        raise HTTPException(status_code=400, detail=f"Auth Error: {error}")
    
    if not GOOGLE_CLIENT_SECRET or not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Server config missing")
        
    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to retrieve token from Google")
    
    tokens = response.json()
    id_token_str = tokens.get("id_token")
    
    # Verify ID Token
    google_user_info = verify_google_token(id_token_str)
    
    # Extract user info
    uid = google_user_info.get("sub")
    email = google_user_info.get("email")
    name = google_user_info.get("name")
    picture = google_user_info.get("picture")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided by Google")

    # Upsert user in Firestore
    db = get_firestore()
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        # Update existing user
        user_data = user_doc.to_dict()
        user_data["name"] = name  # Update name if changed
        user_data["picture"] = picture
        # Keep existing role
        role = user_data.get("role", "user")
        user_ref.update({"name": name, "picture": picture})
    else:
        # Create new user
        role = "user"
        # Auto-admin rule (optional, e.g. based on domain or specific email)
        # if email == "admin@slim.ai": role = "admin"
        
        new_user = User(
            uid=uid,
            email=email,
            name=name,
            picture=picture,
            role=role,
            created_at=datetime.utcnow()
        )
        user_ref.set(new_user.model_dump())
    
    # Create valid backend access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": uid, "email": email, "role": role},
        expires_delta=access_token_expires
    )
    
    # Redirect to React frontend with token
    frontend_redirect = f"{FRONTEND_URL}/dashboard?token={access_token}" 
    return RedirectResponse(frontend_redirect)

@router.get("/me", response_model=User)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
