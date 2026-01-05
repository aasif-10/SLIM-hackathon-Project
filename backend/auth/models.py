from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class User(BaseModel):
    uid: str
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    role: str = "user"  # admin, researcher, viewer
    created_at: datetime = Field(default_factory=datetime.utcnow)
    disabled: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    uid: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
