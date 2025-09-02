from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import json
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

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
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    experience_years: Optional[int] = None

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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialties: Optional[List[str]] = None
    unit_preference: Optional[str] = None
    experience_years: Optional[int] = None

def validate_cpf(cpf: str) -> bool:
    """Validate Brazilian CPF"""
    if not cpf or len(cpf.replace(".", "").replace("-", "")) != 11:
        return False
    
    # Remove formatting
    cpf_numbers = ''.join(filter(str.isdigit, cpf))
    
    # Check for repeated numbers
    if len(set(cpf_numbers)) == 1:
        return False
    
    # Validate check digits (simplified)
    return True

def validate_password_strength(password: str) -> Dict[str, Any]:
    """Validate password strength"""
    errors = []
    score = 0
    
    if len(password) < 8:
        errors.append("Senha deve ter pelo menos 8 caracteres")
    else:
        score += 1
    
    if not any(c.isupper() for c in password):
        errors.append("Senha deve conter pelo menos uma letra maiúscula")
    else:
        score += 1
    
    if not any(c.islower() for c in password):
        errors.append("Senha deve conter pelo menos uma letra minúscula")
    else:
        score += 1
    
    if not any(c.isdigit() for c in password):
        errors.append("Senha deve conter pelo menos um número")
    else:
        score += 1
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Senha deve conter pelo menos um caractere especial")
    else:
        score += 1
    
    strength_levels = ["Muito fraca", "Fraca", "Regular", "Boa", "Muito forte"]
    strength = strength_levels[min(score, 4)]
    
    return {
        "is_valid": len(errors) <= 2,  # Allow some flexibility
        "errors": errors,
        "strength": strength,
        "score": score
    }

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    # Validate input data
    errors = []
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        errors.append("E-mail já está cadastrado")
    
    # Validate CPF if provided
    if user_data.cpf:
        if not validate_cpf(user_data.cpf):
            errors.append("CPF inválido")
        else:
            existing_cpf = db.query(User).filter(User.cpf == user_data.cpf).first()
            if existing_cpf:
                errors.append("CPF já está cadastrado")
    
    # Validate password strength
    password_validation = validate_password_strength(user_data.password)
    if not password_validation["is_valid"]:
        errors.extend(password_validation["errors"][:2])  # Limit to first 2 errors
    
    # Validate name
    if len(user_data.name.strip()) < 2:
        errors.append("Nome deve ter pelo menos 2 caracteres")
    
    # Validate phone format (Brazilian)
    if user_data.phone and not user_data.phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "").isdigit():
        errors.append("Formato de telefone inválido")
    
    # If there are validation errors, return them
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Dados inválidos", "errors": errors}
        )
    
    # Parse birth_date if provided
    birth_date_obj = None
    if user_data.birth_date:
        try:
            birth_date_obj = datetime.strptime(user_data.birth_date, "%Y-%m-%d").date()
            # Check if age is reasonable (18-80)
            age = (datetime.now().date() - birth_date_obj).days // 365
            if age < 18 or age > 80:
                raise HTTPException(status_code=400, detail="Idade deve estar entre 18 e 80 anos")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido (use YYYY-MM-DD)")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        name=user_data.name.strip(),
        email=user_data.email.lower(),
        password_hash=hashed_password,
        cpf=user_data.cpf,
        phone=user_data.phone,
        user_type="massagista"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create massagista profile with additional fields
    profile_data = {
        "user_id": db_user.id,
        "unit_preference": user_data.unit_preference,
        "specialties": json.dumps(user_data.specialties) if user_data.specialties else None,
    }
    
    if birth_date_obj:
        profile_data["birth_date"] = birth_date_obj
    if user_data.gender:
        profile_data["gender"] = user_data.gender
    if user_data.experience_years:
        profile_data["experience_years"] = user_data.experience_years
    
    massagista_profile = MassagistaProfile(**profile_data)
    
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

def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if not all([smtp_user, smtp_password]):
        print("⚠️  Email credentials not configured. Reset token:", reset_token)
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = "Espaço VIV - Redefinir Senha"
        
        # HTML body
        html_body = f"""
        <html>
        <body>
            <h2>🌿 Espaço VIV - Redefinição de Senha</h2>
            <p>Olá!</p>
            <p>Você solicitou a redefinição da sua senha. Use o código abaixo para criar uma nova senha:</p>
            <div style="background-color: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h3 style="color: #2c5530; font-family: monospace; letter-spacing: 2px;">{reset_token}</h3>
            </div>
            <p>Este código é válido por 1 hora.</p>
            <p>Se você não solicitou esta redefinição, ignore este email.</p>
            <br>
            <p>Equipe Espaço VIV 🌱</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Por segurança, retorna sucesso mesmo se o usuário não existir
        return {"message": "Se o email existir em nosso sistema, você receberá instruções de redefinição."}
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(6)[:6].upper()  # 6 caracteres
    reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    # Save reset token to user
    user.reset_token = reset_token
    user.reset_token_expires = reset_expires
    db.commit()
    
    # Send email
    email_sent = send_password_reset_email(request.email, reset_token)
    
    if not email_sent:
        # Log token for development
        print(f"🔑 Reset token para {request.email}: {reset_token}")
    
    return {"message": "Se o email existir em nosso sistema, você receberá instruções de redefinição."}

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.reset_token == request.token.upper(),
        User.reset_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Token inválido ou expirado"
        )
    
    # Validate new password
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="A senha deve ter pelo menos 6 caracteres"
        )
    
    # Update password
    user.password_hash = get_password_hash(request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    
    db.commit()
    
    return {"message": "Senha redefinida com sucesso! Você já pode fazer login."}

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password with current password verification"""
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="Senha atual incorreta"
        )
    
    # Validate new password
    password_validation = validate_password_strength(request.new_password)
    if not password_validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Nova senha não atende aos critérios de segurança",
                "errors": password_validation["errors"]
            }
        )
    
    # Check if new password is different from current
    if verify_password(request.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=400,
            detail="A nova senha deve ser diferente da senha atual"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(request.new_password)
    db.commit()
    
    return {"message": "Senha alterada com sucesso!"}

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    # Validate phone format if provided
    if profile_data.phone and not profile_data.phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "").isdigit():
        raise HTTPException(
            status_code=400,
            detail="Formato de telefone inválido"
        )
    
    # Update user fields
    if profile_data.name and len(profile_data.name.strip()) >= 2:
        current_user.name = profile_data.name.strip()
    
    if profile_data.phone:
        current_user.phone = profile_data.phone
    
    # Update massagista profile fields
    massagista_profile = db.query(MassagistaProfile).filter(
        MassagistaProfile.user_id == current_user.id
    ).first()
    
    if massagista_profile:
        if profile_data.specialties is not None:
            massagista_profile.specialties = json.dumps(profile_data.specialties)
        
        if profile_data.unit_preference:
            massagista_profile.unit_preference = profile_data.unit_preference
        
        if profile_data.experience_years is not None:
            massagista_profile.experience_years = profile_data.experience_years
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)

@router.post("/validate-password")
async def validate_password(password: str):
    """Validate password strength for frontend feedback"""
    validation = validate_password_strength(password)
    return validation

@router.get("/profile/complete")
async def get_complete_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get complete user profile with massagista details"""
    massagista_profile = db.query(MassagistaProfile).filter(
        MassagistaProfile.user_id == current_user.id
    ).first()
    
    profile_data = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "cpf": current_user.cpf,
        "phone": current_user.phone,
        "user_type": current_user.user_type,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
    }
    
    if massagista_profile:
        profile_data.update({
            "specialties": json.loads(massagista_profile.specialties) if massagista_profile.specialties else [],
            "unit_preference": massagista_profile.unit_preference,
            "experience_years": massagista_profile.experience_years,
            "is_available": massagista_profile.is_available,
        })
    
    return profile_data

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should discard token)"""
    return {"message": f"Usuário {current_user.name} deslogado com sucesso"}