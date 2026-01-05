from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from auth.utils import SECRET_KEY, ALGORITHM
from auth.models import TokenData, User
from firebase_client import get_firestore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid: str = payload.get("sub")
        email: str = payload.get("email")
        role: str = payload.get("role")
        
        if uid is None:
            raise credentials_exception
        token_data = TokenData(uid=uid, email=email, role=role)
    except JWTError:
        raise credentials_exception
        
    # Verify user exists in Firestore (stateless but verified)
    db = get_firestore()
    user_ref = db.collection("users").document(token_data.uid)
    user_doc = user_ref.get()
    
    if not user_doc.exists:
        raise credentials_exception
        
    user_data = user_doc.to_dict()
    return User(**user_data)

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "admin":
         raise HTTPException(status_code=403, detail="Not authorized")
    return current_user
