from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import json

from database.connection import get_db
from models.users import User, MassagistaProfile
from utils.auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter()
security = HTTPBearer()

# Pydantic models
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    cpf: Optional[str] = None
    phone: Optional[str] = None
    unit_preference: Optional[str] = None
    specialties: Optional[List[str]] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    user_type: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Check CPF if provided
    if user_data.cpf:
        existing_cpf = db.query(User).filter(User.cpf == user_data.cpf).first()
        if existing_cpf:
            raise HTTPException(
                status_code=400,
                detail="CPF already registered"
            )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        cpf=user_data.cpf,
        phone=user_data.phone,
        user_type="massagista"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create massagista profile
    massagista_profile = MassagistaProfile(
        user_id=db_user.id,
        specialties=json.dumps(user_data.specialties) if user_data.specialties else None,
        unit_preference=user_data.unit_preference
    )
    
    db.add(massagista_profile)
    db.commit()
    
    return UserResponse.from_orm(db_user)

@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user or not verify_password(user_credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Update allowed fields
    allowed_fields = {"name", "phone"}
    for field, value in user_update.items():
        if field in allowed_fields and hasattr(current_user, field):
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)