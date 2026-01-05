import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.auth.utils import create_access_token, verify_google_token
from backend.auth.models import User
from jose import jwt
from backend.auth.utils import SECRET_KEY, ALGORITHM

def test_jwt_generation():
    print("Testing JWT Generation...")
    data = {"sub": "test_uid", "email": "test@example.com", "role": "user"}
    token = create_access_token(data)
    print(f"Token generated: {token[:20]}...")
    
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "test_uid"
    assert decoded["email"] == "test@example.com"
    print("✅ JWT Generation and Decoding Passed")

def test_user_model():
    print("\nTesting User Model...")
    user = User(uid="123", email="test@slim.ai")
    assert user.role == "user"
    assert user.disabled is False
    print(f"User created: {user}")
    print("✅ User Model Passed")

if __name__ == "__main__":
    try:
        test_jwt_generation()
        test_user_model()
        print("\nAll dry-run tests passed!")
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        exit(1)
