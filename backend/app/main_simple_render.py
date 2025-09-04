from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import hashlib
import jwt
from jwt.exceptions import DecodeError, ExpiredSignatureError
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import calendar as cal
from collections import defaultdict
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Database imports
from app.database import get_db, create_tables, init_db
from app.models import User, Unit, Service, Booking, PasswordReset
from app import crud

# Carrega as variaveis de ambiente do arquivo .env
load_dotenv()

def validate_email_configuration():
    """Validate email configuration on startup"""
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if email_enabled and all([smtp_user, smtp_password]):
        print("[EMAIL] Sistema de email configurado e ativado")
        print(f"[EMAIL] Servidor SMTP: {os.getenv('SMTP_SERVER', 'smtp.gmail.com')}")
        print(f"[EMAIL] Usuario: {smtp_user}")
    elif email_enabled and not all([smtp_user, smtp_password]):
        print("[EMAIL] AVISO: Email ativado mas credenciais incompletas")
    else:
        print("[EMAIL] Sistema de email desativado")

# Validate email configuration on startup
validate_email_configuration()

app = FastAPI(
    title="Espaco VIV API - Render",
    description="API para sistema de agendamento de massagens",
    version="1.0.0"
)

# Initialize database tables and data
create_tables()
init_db()

# CORS - mais permissivo para testes iniciais
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações
SECRET_KEY = os.getenv("SECRET_KEY", "espacoviv-render-key-2024")
ALGORITHM = "HS256"

# ============================================================================
# MODELOS
# ============================================================================

class SpecialtyPrice(BaseModel):
    specialty: str
    price: float

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    cpf: Optional[str] = None
    phone: Optional[str] = None
    unit_preference: Optional[str] = None
    specialties: List[str] = []
    specialty_prices: List[SpecialtyPrice] = []
    birth_date: Optional[str] = None
    gender: Optional[str] = None
    experience_years: Optional[int] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class BookingCreate(BaseModel):
    client_name: str
    client_phone: str
    unit_code: str
    massagista_id: int
    service: str
    appointment_date: date
    appointment_time: str
    notes: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class AvailabilityRequest(BaseModel):
    date: str
    status: str  # 'available' or 'unavailable'
    time_slots: List[str] = []

class WeekAvailabilityRequest(BaseModel):
    dates: List[str]
    status: str
    time_slots: List[str] = []

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialties: Optional[List[str]] = None
    specialty_prices: Optional[List[SpecialtyPrice]] = None
    unit_preference: Optional[str] = None
    experience_years: Optional[int] = None

class DayAvailability(BaseModel):
    date: str
    day_of_week: str
    available_slots: List[str]
    booked_slots: List[str]
    total_slots: int
    available_count: int
    is_weekend: bool
    is_holiday: bool = False

class TimeSlotInfo(BaseModel):
    time: str
    available: bool
    booked_by: Optional[str] = None
    service: Optional[str] = None
    massagista_name: Optional[str] = None

class AdvancedDayView(BaseModel):
    date: str
    unit_name: str
    slots: List[TimeSlotInfo]
    total_bookings: int
    revenue_estimate: float

# ============================================================================
# DATABASE INTEGRATION - REPLACING IN-MEMORY STORAGE
# ============================================================================

# Password reset tokens (temporary storage for tokens)
# This will be replaced by database PasswordReset table
password_reset_tokens = {}

# Availability database - structure: {user_id: {date: {status, time_slots}}}
# This will be extended later with proper database tables
availability_db = {}

# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

# Password functions moved to crud.py - using CRUD functions
# def hash_password and verify_password are now in crud module

def create_access_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str, db: Session = None) -> Dict:
    """Verify JWT token and return user data"""
    if db is None:
        # This should not happen in normal flow, but provides fallback
        raise HTTPException(status_code=401, detail="Erro interno do servidor")
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalido")
        
        # Find user in database
        user = crud.get_user_by_id(db, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado")
        
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "created_at": user.created_at,
            "is_active": user.is_active
        }
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except DecodeError:
        raise HTTPException(status_code=401, detail="Token invalido")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro na validacao do token: {str(e)}")

# get_next_id function is no longer needed - database handles auto-increment IDs

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> Dict:
    """Dependency to get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de acesso requerido")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Esquema de autenticacao invalido")
    except ValueError:
        raise HTTPException(status_code=401, detail="Formato de token invalido")
    
    return verify_access_token(token, db)

def validate_cpf(cpf: str) -> bool:
    """Validate Brazilian CPF"""
    if not cpf or len(cpf.replace(".", "").replace("-", "")) != 11:
        return False
    
    cpf_numbers = ''.join(filter(str.isdigit, cpf))
    if len(set(cpf_numbers)) == 1:
        return False
    
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
        "is_valid": len(errors) <= 2,
        "errors": errors,
        "strength": strength,
        "score": score
    }

def send_password_reset_email(email: str, reset_token: str):
    """Send password reset email with professional configuration"""
    # Email configuration from environment variables
    email_enabled = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_name = os.getenv("EMAIL_FROM_NAME", "Espaco VIV")
    reply_to = os.getenv("EMAIL_REPLY_TO", "noreply@espacoviv.com")
    
    # Check if email is enabled and configured
    if not email_enabled:
        print(f"[EMAIL] Email desabilitado. Token de reset para {email}: {reset_token}")
        return False
        
    if not all([smtp_user, smtp_password]):
        print(f"[EMAIL] Configuracao incompleta. Token de reset para {email}: {reset_token}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{from_name} <{smtp_user}>"
        msg['To'] = email
        msg['Reply-To'] = reply_to
        msg['Subject'] = "Espaco VIV - Codigo de Redefinicao de Senha"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Espaco VIV - Redefinicao de Senha</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #47103C 0%, #6B2154 100%); padding: 30px; border-radius: 10px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 24px;">Espaco VIV</h1>
                    <p style="color: #f0f0f0; margin: 10px 0 0 0;">Redefinicao de Senha</p>
                </div>
                
                <div style="padding: 30px; background: #f9f9f9; border-radius: 10px; margin-top: 20px;">
                    <h2 style="color: #47103C; margin-top: 0;">Ola!</h2>
                    <p>Voce solicitou a redefinicao da sua senha. Use o codigo de verificacao abaixo:</p>
                    
                    <div style="background: white; padding: 25px; border-radius: 8px; text-align: center; margin: 25px 0; border: 2px dashed #47103C;">
                        <h2 style="color: #47103C; font-family: 'Courier New', monospace; letter-spacing: 3px; margin: 0; font-size: 28px;">{reset_token}</h2>
                    </div>
                    
                    <div style="background: #fff3cd; border: 1px solid #ffeeba; border-radius: 5px; padding: 15px; margin: 20px 0;">
                        <p style="margin: 0; font-size: 14px; color: #856404;">
                            <strong>Importante:</strong> Este codigo e valido por 1 hora. Se voce nao solicitou esta redefinicao, ignore este email.
                        </p>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px; padding: 20px; color: #666; font-size: 12px;">
                    <p>Esta mensagem foi enviada automaticamente pelo sistema Espaco VIV.</p>
                    <p>Para duvidas, entre em contato conosco.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 15px 0;">
                    <p>&copy; 2024 Espaco VIV. Todos os direitos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        
        print(f"[EMAIL] Email de redefinicao enviado com sucesso para {email}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print(f"[EMAIL] ERRO: Falha na autenticacao SMTP para {email}")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL] ERRO SMTP ao enviar para {email}: {str(e)}")
        return False
    except Exception as e:
        print(f"[EMAIL] ERRO geral ao enviar para {email}: {str(e)}")
        return False

def get_default_slots(target_date: date) -> List[str]:
    """Get default time slots based on day of week"""
    if target_date.weekday() >= 5:  # Weekend
        return ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00"]
    return ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]

def is_holiday(target_date: date) -> bool:
    """Check if date is a Brazilian holiday"""
    holidays_2024 = [
        date(2024, 1, 1), date(2024, 4, 21), date(2024, 9, 7), 
        date(2024, 10, 12), date(2024, 11, 15), date(2024, 12, 25),
    ]
    return target_date in holidays_2024

# ============================================================================
# ROTAS
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Espaco VIV API no Render funcionando!",
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "database": "in-memory (temporario)"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "users": 0,
            "bookings": 0,
            "units": 3,
            "services": 15
        }
    }

# AUTH
@app.post("/api/auth/register")
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    print(f"Dados recebidos para registro: {user_data}")
    print(f"Especialidades: {user_data.specialties}")
    print(f"Precos especialidades: {user_data.specialty_prices}")
    errors = []
    
    # Check if user already exists
    existing_user = crud.get_user_by_email(db, user_data.email)
    if existing_user:
        errors.append("E-mail ja esta cadastrado")
    
    # Validate CPF if provided
    if user_data.cpf:
        if not validate_cpf(user_data.cpf):
            errors.append("CPF invalido")
        # CPF uniqueness check would need additional logic - simplified for now
    
    # Validate password strength
    password_validation = validate_password_strength(user_data.password)
    if not password_validation["is_valid"]:
        errors.extend(password_validation["errors"][:2])
    
    # Validate name
    if len(user_data.name.strip()) < 2:
        errors.append("Nome deve ter pelo menos 2 caracteres")
    
    # Validate phone format
    if user_data.phone and not user_data.phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "").isdigit():
        errors.append("Formato de telefone invalido")
    
    # Validate specialty prices
    if user_data.specialty_prices:
        specialty_names = [sp.specialty for sp in user_data.specialty_prices]
        if len(set(specialty_names)) != len(specialty_names):
            errors.append("Nao e possivel definir o mesmo preco duas vezes para a mesma especialidade")
        
        for sp in user_data.specialty_prices:
            if sp.price <= 0:
                errors.append(f"Preco para {sp.specialty} deve ser maior que zero")
            if sp.price > 5000:
                errors.append(f"Preco para {sp.specialty} nao pode exceder R$ 5.000")
            if sp.specialty not in user_data.specialties:
                errors.append(f"Preco definido para especialidade nao selecionada: {sp.specialty}")
    
    # If there are validation errors, return them
    if errors:
        raise HTTPException(
            status_code=400,
            detail={"message": "Dados invalidos", "errors": errors}
        )
    
    # Parse birth_date if provided
    birth_date_obj = None
    if user_data.birth_date:
        try:
            birth_date_obj = datetime.strptime(user_data.birth_date, "%Y-%m-%d").date()
            age = (datetime.now().date() - birth_date_obj).days // 365
            if age < 18 or age > 80:
                raise HTTPException(status_code=400, detail="Idade deve estar entre 18 e 80 anos")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido (use YYYY-MM-DD)")
    
    # Create user in database
    user_dict = {
        "name": user_data.name.strip(),
        "email": user_data.email.lower(),
        "password": user_data.password,  # CRUD function will hash it
        "phone": user_data.phone,
        "user_type": "massagista" if user_data.specialties else "client",
        "unit_preference": user_data.unit_preference,
    }
    
    new_user = crud.create_user(db, user_dict)
    
    # Save specialties if user is a massagista
    if user_data.specialties:
        from app.models import UserSpecialty, Service
        for specialty in user_data.specialties:
            # Find or create service
            service = db.query(Service).filter(Service.name == specialty).first()
            if service:
                # Get custom price if provided
                custom_price = None
                for sp in user_data.specialty_prices:
                    if sp.specialty == specialty:
                        custom_price = sp.price
                        break
                
                # Create user specialty association
                user_specialty = UserSpecialty(
                    user_id=new_user.id,
                    service_id=service.id,
                    custom_price=custom_price
                )
                db.add(user_specialty)
        
        db.commit()
    
    print(f"Usuario salvo no banco: {new_user.id}")
    print(f"Tipo de usuario: {user_dict['user_type']}")
    print(f"Especialidades: {user_data.specialties}")
    print(f"Precos salvos: {[sp.dict() for sp in user_data.specialty_prices]}")
    return {"message": "Usuario cadastrado com sucesso", "user_id": new_user.id}

@app.post("/api/auth/login")
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, login_data.email)
    
    if not user or not crud.verify_password(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="E-mail ou senha invalidos")
    
    access_token = create_access_token(user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    }

@app.get("/api/auth/me")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current user information from JWT token"""
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "unit_preference": "",  # Placeholder - can be filled from database if needed
        "specialties": [],  # Placeholder - can be filled from database if needed
        "specialty_prices": [],  # Placeholder - can be filled from database if needed
        "massage_types": "",  # Placeholder - can be filled from database if needed
        "phone": current_user.get("phone", ""),
        "is_online": True
    }

# UNITS
@app.get("/api/units")
async def get_units():
    return units_db

# MASSAGISTAS
@app.get("/api/massagista/by-unit/{unit_code}")
async def get_massagistas_by_unit(unit_code: str, db: Session = Depends(get_db)):
    from app.models import User, UserSpecialty, Service
    print(f"Buscando massagistas para unidade: {unit_code}")
    
    # Get all users that are massagistas and match the unit preference
    users = db.query(User).filter(
        User.user_type == "massagista",
        User.is_active == True
    ).all()
    
    # Filter by unit if specified
    if unit_code != "all":
        users = [u for u in users if u.unit_preference == unit_code]
    
    massagistas = []
    for user in users:
        # Get specialties for this user
        specialties = []
        specialty_prices = []
        
        for us in user.specialties:
            service = us.service
            specialties.append(service.name)
            # Use custom price if available, otherwise use service default
            price = us.custom_price if us.custom_price else service.price
            specialty_prices.append(price)
        
        # If no specialties stored, use defaults
        if not specialties:
            specialties = ["Massagem Relaxante", "Drenagem Linfática"]
            specialty_prices = [80.0, 90.0]
        
        massagista_data = {
            "id": user.id,
            "name": user.name,
            "specialties": specialties,
            "specialty_prices": specialty_prices,
            "is_available": True,
            "avatar_url": "/static/assets/images/default-avatar.png"
        }
        massagistas.append(massagista_data)
    
    print(f"Retornando {len(massagistas)} massagistas do banco de dados")
    return massagistas

# BOOKINGS
@app.post("/api/bookings")
async def create_booking(booking_data: BookingCreate):
    unit = next((u for u in units_db if u["code"] == booking_data.unit_code), None)
    if not unit:
        raise HTTPException(status_code=400, detail="Unidade não encontrada")
    
    # Mock massagista validation for now
    valid_massagista_ids = [1, 2, 3, 4]
    if booking_data.massagista_id not in valid_massagista_ids:
        raise HTTPException(status_code=400, detail="Massagista não encontrada")
    
    new_booking = {
        "id": get_next_id(bookings_db),
        "client_name": booking_data.client_name,
        "client_phone": booking_data.client_phone,
        "unit_code": booking_data.unit_code,
        "massagista_id": booking_data.massagista_id,
        "service": booking_data.service,
        "appointment_date": booking_data.appointment_date,
        "appointment_time": booking_data.appointment_time,
        "status": "pending",
        "notes": booking_data.notes or "",
        "created_at": datetime.now()
    }
    
    bookings_db.append(new_booking)
    
    return {
        "message": "Agendamento criado com sucesso!",
        "booking_id": new_booking["id"],
        "status": "pending"
    }

@app.get("/api/bookings/available-times/{massagista_id}/{date}")
async def get_available_times(massagista_id: int, date: str):
    # Mock massagista validation for now
    valid_massagista_ids = [1, 2, 3, 4]
    if massagista_id not in valid_massagista_ids:
        raise HTTPException(status_code=404, detail="Massagista não encontrada")
    
    try:
        appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
        if appointment_date < datetime.now().date():
            return []
        
        # Buscar horários configurados pelo massagista para esta data
        configured_times = []
        if massagista_id in availability_db and date in availability_db[massagista_id]:
            day_availability = availability_db[massagista_id][date]
            if day_availability.get("status") == "available":
                configured_times = day_availability.get("time_slots", [])
        
        # Se não há configuração específica, usar horários padrão
        if not configured_times:
            configured_times = ["08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30", 
                               "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", 
                               "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30", "20:00", "20:30"]
        
        # Remove horários ocupados
        booked_times = [
            b["appointment_time"] for b in bookings_db 
            if b["massagista_id"] == massagista_id and b["appointment_date"] == appointment_date
            and b["status"] in ["pending", "confirmed"]
        ]
        
        available = [t for t in configured_times if t not in booked_times]
        return available
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

# FORGOT PASSWORD
@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, request.email)
    
    if not user:
        # Don't reveal if email doesn't exist - security measure
        return {"message": "Se o email existir em nosso sistema, voce recebera instrucoes de redefinicao."}
    
    # Create password reset token in database
    password_reset = crud.create_password_reset_token(db, user.id)
    
    # Try to send the email
    email_sent = send_password_reset_email(request.email, password_reset.token)
    
    # Always return the same message for security (don't reveal if email exists)
    return {
        "message": "Se o email existir em nosso sistema, voce recebera um codigo de verificacao.",
        "details": "Verifique sua caixa de entrada e spam. O codigo expira em 1 hora."
    }

@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    # Try to reset password using the token
    success = crud.reset_user_password(db, request.token, request.new_password)
    
    if not success:
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")
    
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")
    
    return {"message": "Senha redefinida com sucesso! Voce ja pode fazer login."}

@app.post("/api/auth/validate-password")
async def validate_password_endpoint(request: dict):
    password = request.get("password", "")
    return validate_password_strength(password)

# CALENDAR APIS
@app.get("/api/calendar/availability/day/{unit_code}/{date}")
async def get_day_availability(unit_code: str, date: str):
    unit = next((u for u in units_db if u["code"] == unit_code), None)
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    existing_bookings = [b for b in bookings_db 
                        if b["unit_code"] == unit_code 
                        and b["appointment_date"] == target_date
                        and b["status"] in ["pending", "confirmed"]]
    
    booked_times = [b["appointment_time"] for b in existing_bookings]
    all_slots = get_default_slots(target_date)
    
    slots = []
    for time_slot in all_slots:
        booking = next((b for b in existing_bookings if b["appointment_time"] == time_slot), None)
        massagista_name = None
        if booking:
            # Mock massagista name lookup
            massagista_names = {1: "Maria Silva", 2: "Ana Costa", 3: "Carla Santos", 4: "Fernanda Oliveira"}
            massagista_name = massagista_names.get(booking["massagista_id"], "Massagista")
        
        slot_info = TimeSlotInfo(
            time=time_slot,
            available=booking is None,
            booked_by=booking["client_name"] if booking else None,
            service=booking["service"] if booking else None,
            massagista_name=massagista_name
        )
        slots.append(slot_info)
    
    revenue_estimate = len(existing_bookings) * 100.0
    
    return AdvancedDayView(
        date=date,
        unit_name=unit["name"],
        slots=slots,
        total_bookings=len(existing_bookings),
        revenue_estimate=revenue_estimate
    )

@app.get("/api/calendar/next-available/{unit_code}")
async def find_next_available_slot(unit_code: str, from_date: Optional[str] = None):
    unit = next((u for u in units_db if u["code"] == unit_code), None)
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    if from_date:
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        start_date = datetime.now().date()
    
    for i in range(30):
        check_date = start_date + timedelta(days=i)
        
        existing_bookings = [b for b in bookings_db 
                           if b["unit_code"] == unit_code 
                           and b["appointment_date"] == check_date
                           and b["status"] in ["pending", "confirmed"]]
        
        booked_times = [b["appointment_time"] for b in existing_bookings]
        available_slots = get_default_slots(check_date)
        
        for slot in available_slots:
            if slot not in booked_times:
                return {
                    "next_available": {
                        "date": check_date.strftime("%Y-%m-%d"),
                        "time": slot,
                        "day_of_week": check_date.strftime("%A"),
                        "days_from_now": i
                    },
                    "alternatives": [
                        {
                            "time": alt_slot,
                            "available": alt_slot not in booked_times
                        }
                        for alt_slot in available_slots[:5]
                    ]
                }
    
    return {"message": "No available slots found in the next 30 days"}

# SERVICES
@app.get("/api/services")
async def get_services():
    return services_db

# NOVOS ENDPOINTS FUNCIONAIS
@app.post("/api/test/availability/day/{date}")
async def test_day_availability(date: str, request: Request):
    try:
        body = await request.body()
        import json
        data = json.loads(body)
        
        status = data.get("status", "")
        time_slots = data.get("time_slots", [])
        
        print(f"SUCESSO Day {date}: status={status}, slots={len(time_slots)}")
        
        user_id = 1
        if user_id not in availability_db:
            availability_db[user_id] = {}
        
        availability_db[user_id][date] = {
            "status": status,
            "time_slots": time_slots
        }
        
        return {"message": "OK"}
    except Exception as e:
        print(f"ERRO Day: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/availability/week")
async def test_week_availability(request: Request):
    try:
        body = await request.body()
        import json
        data = json.loads(body)
        
        dates = data.get("dates", [])
        status = data.get("status", "")
        time_slots = data.get("time_slots", [])
        
        print(f"SUCESSO Week: {len(dates)} dates, status={status}, slots={len(time_slots)}")
        
        user_id = 1
        if user_id not in availability_db:
            availability_db[user_id] = {}
        
        for date_str in dates:
            availability_db[user_id][date_str] = {
                "status": status,
                "time_slots": time_slots
            }
        
        return {"message": "OK"}
    except Exception as e:
        print(f"ERRO Week: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/calendar/day/{date}")
async def get_saved_day_availability(date: str):
    try:
        user_id = 1
        if user_id not in availability_db or date not in availability_db[user_id]:
            print(f"GET Day {date}: VAZIO")
            return {"status": "available", "time_slots": []}
        
        data = availability_db[user_id][date]
        print(f"GET Day {date}: {data}")
        return data
    except Exception as e:
        print(f"ERRO GET Day: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/today")
async def get_today_appointments(db: Session = Depends(get_db)):
    try:
        user_id = 1
        today = datetime.now().date()
        
        # Get today's bookings from database
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        bookings = db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.booking_date >= start_of_day,
            Booking.booking_date <= end_of_day
        ).all()
        
        today_bookings = []
        for booking in bookings:
            booking_dict = {
                "id": booking.id,
                "client_name": f"Cliente {booking.id}",  # Placeholder since we don't have this field
                "client_phone": "N/A",  # Placeholder
                "service": "Massagem",  # Placeholder
                "appointment_date": booking.booking_date.date().isoformat(),
                "appointment_time": booking.booking_date.time().strftime("%H:%M"),
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None
            }
            today_bookings.append(booking_dict)
        
        print(f"Agendamentos hoje para user {user_id}: {len(today_bookings)}")
        return today_bookings
    except Exception as e:
        print(f"ERRO Today Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/week")
async def get_week_appointments(db: Session = Depends(get_db)):
    try:
        user_id = 1
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Get week's bookings from database
        start_datetime = datetime.combine(start_of_week, datetime.min.time())
        end_datetime = datetime.combine(end_of_week, datetime.max.time())
        
        bookings = db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.booking_date >= start_datetime,
            Booking.booking_date <= end_datetime
        ).all()
        
        week_bookings = []
        for booking in bookings:
            booking_dict = {
                "id": booking.id,
                "client_name": f"Cliente {booking.id}",  # Placeholder
                "client_phone": "N/A",  # Placeholder
                "service": "Massagem",  # Placeholder
                "appointment_date": booking.booking_date.date().isoformat(),
                "appointment_time": booking.booking_date.time().strftime("%H:%M"),
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None
            }
            week_bookings.append(booking_dict)
        
        print(f"Agendamentos desta semana para user {user_id}: {len(week_bookings)}")
        return week_bookings
    except Exception as e:
        print(f"ERRO Week Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/month")
async def get_month_appointments(db: Session = Depends(get_db)):
    try:
        user_id = 1
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        next_month = start_of_month.replace(month=start_of_month.month % 12 + 1) if start_of_month.month < 12 else start_of_month.replace(year=start_of_month.year + 1, month=1)
        end_of_month = next_month - timedelta(days=1)
        
        # Get month's bookings from database
        start_datetime = datetime.combine(start_of_month, datetime.min.time())
        end_datetime = datetime.combine(end_of_month, datetime.max.time())
        
        bookings = db.query(Booking).filter(
            Booking.user_id == user_id,
            Booking.booking_date >= start_datetime,
            Booking.booking_date <= end_datetime
        ).all()
        
        month_bookings = []
        for booking in bookings:
            booking_dict = {
                "id": booking.id,
                "client_name": f"Cliente {booking.id}",  # Placeholder
                "client_phone": "N/A",  # Placeholder
                "service": "Massagem",  # Placeholder
                "appointment_date": booking.booking_date.date().isoformat(),
                "appointment_time": booking.booking_date.time().strftime("%H:%M"),
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None
            }
            month_bookings.append(booking_dict)
        
        print(f"Agendamentos deste mês para user {user_id}: {len(month_bookings)}")
        return month_bookings
    except Exception as e:
        print(f"ERRO Month Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/all")
async def get_all_appointments(db: Session = Depends(get_db)):
    try:
        user_id = 1
        
        # Get all bookings from database for this user
        bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
        
        all_bookings = []
        for booking in bookings:
            booking_dict = {
                "id": booking.id,
                "client_name": f"Cliente {booking.id}",  # Placeholder
                "client_phone": "N/A",  # Placeholder
                "service": "Massagem",  # Placeholder
                "appointment_date": booking.booking_date.date().isoformat(),
                "appointment_time": booking.booking_date.time().strftime("%H:%M"),
                "status": booking.status,
                "created_at": booking.created_at.isoformat() if booking.created_at else None
            }
            all_bookings.append(booking_dict)
        
        print(f"Total agendamentos para user {user_id}: {len(all_bookings)}")
        return all_bookings
    except Exception as e:
        print(f"ERRO All Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AVAILABILITY/CALENDAR APIs
@app.put("/api/massagista/availability/{date}")
async def set_day_availability(date: str, request: Request):
    """Set availability for a specific day"""
    try:
        # Lê o body da requisição diretamente
        body = await request.body()
        print(f"Raw body recebido para dia {date}: {body}")
        
        # Parse manual do JSON
        import json
        data = json.loads(body)
        print(f"Dados parseados para dia {date}: {data}")
        
        status = data.get("status", "")
        time_slots = data.get("time_slots", [])
        
        print(f"Date: {date}")
        print(f"Status: {status}")
        print(f"Time slots: {time_slots}")
        
        # Temporariamente usando user_id fixo para teste
        user_id = 1
        
        if user_id not in availability_db:
            availability_db[user_id] = {}
        
        availability_db[user_id][date] = {
            "status": status,
            "time_slots": time_slots
        }
        
        print(f"Sucesso! Dados salvos para dia {date} user {user_id}")
        return {"message": f"Disponibilidade para {date} atualizada com sucesso"}
        
    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/availability/{date}")
async def get_day_availability(date: str, current_user: Dict = Depends(get_current_user)):
    """Get availability for a specific day"""
    user_id = current_user["id"]
    
    if user_id not in availability_db or date not in availability_db[user_id]:
        return {"status": "unavailable", "time_slots": []}
    
    return availability_db[user_id][date]

@app.put("/api/test/week-data")
async def test_week_data(request: WeekAvailabilityRequest):
    """Endpoint para testar validação dos dados"""
    print(f"Dados recebidos com sucesso!")
    print(f"Dates: {request.dates}")
    print(f"Status: {request.status}")
    print(f"Time slots: {request.time_slots}")
    return {"message": "Dados validados com sucesso", "data": request}

@app.put("/api/massagista/availability/week")
async def set_week_availability(request: Request):
    """Set availability for entire week"""
    try:
        # Lê o body da requisição diretamente
        body = await request.body()
        print(f"Raw body recebido: {body}")
        
        # Parse manual do JSON
        import json
        data = json.loads(body)
        print(f"Dados parseados: {data}")
        
        dates = data.get("dates", [])
        status = data.get("status", "")
        time_slots = data.get("time_slots", [])
        
        print(f"Dates: {dates}")
        print(f"Status: {status}")
        print(f"Time slots: {time_slots}")
        
        # Temporariamente usando user_id fixo para teste
        user_id = 1
        
        if user_id not in availability_db:
            availability_db[user_id] = {}
        
        # Set availability for all provided dates
        for date_str in dates:
            availability_db[user_id][date_str] = {
                "status": status,
                "time_slots": time_slots
            }
        
        print(f"Sucesso! Dados salvos para user {user_id}")
        return {"message": f"Semana marcada como {status}"}
        
    except Exception as e:
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/availability/month/{year}/{month}")
async def get_month_availability(year: int, month: int, current_user: Dict = Depends(get_current_user)):
    """Get availability for entire month"""
    user_id = current_user["id"]
    
    if user_id not in availability_db:
        return {}
    
    # Filter availability for the requested month
    month_availability = {}
    month_str = f"{year}-{month:02d}"
    
    for date_str, availability in availability_db[user_id].items():
        if date_str.startswith(month_str):
            month_availability[date_str] = availability
    
    return month_availability

# PUBLIC APIs for calendar consultation (no auth needed)
@app.get("/api/massagista/{massagista_id}/availability/month/{year}/{month}")
async def get_massagista_month_availability(massagista_id: int, year: int, month: int):
    """Get public availability for a specific massagista for entire month"""
    if massagista_id not in availability_db:
        return {}
    
    # Filter availability for the requested month
    month_availability = {}
    month_str = f"{year}-{month:02d}"
    
    for date_str, availability in availability_db[massagista_id].items():
        if date_str.startswith(month_str):
            month_availability[date_str] = availability
    
    return month_availability

@app.get("/api/massagista/{massagista_id}/availability/day/{date}")
async def get_massagista_day_availability(massagista_id: int, date: str):
    """Get public availability for a specific massagista for a specific day"""
    if massagista_id not in availability_db:
        return {"status": "unavailable", "time_slots": []}
    
    day_availability = availability_db[massagista_id].get(date, {"status": "unavailable", "time_slots": []})
    return day_availability

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)