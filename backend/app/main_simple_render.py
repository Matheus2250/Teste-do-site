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
# BANCO EM MEMÓRIA (TEMPORÁRIO)
# ============================================================================

users_db = []

units_db = [
    # Sao Paulo (4 unidades)
    {"id": 1, "code": "sp-ingleses", "name": "Sao Paulo - Ingleses [Matriz]", "address": "Bela Vista", "hours": "6h-22h"},
    {"id": 2, "code": "sp-perdizes", "name": "Sao Paulo - Perdizes", "address": "R. Tavares Bastos, 564", "hours": "24h"},
    {"id": 3, "code": "sp-vila-clementino", "name": "Sao Paulo - Vila Clementino", "address": "R. Dr. Bacelar, 82", "hours": "24h"},
    {"id": 4, "code": "sp-prudente", "name": "Sao Paulo - Prudente de Moraes", "address": "R. Prudente de Moraes Neto, 81", "hours": "24h"},
    
    # Rio de Janeiro (2 unidades)
    {"id": 5, "code": "rj-centro", "name": "Rio de Janeiro - Centro", "address": "Av. Rio Branco, 185 - Sala 2103", "hours": "6h-22h"},
    {"id": 6, "code": "rj-copacabana", "name": "Rio de Janeiro - Copacabana", "address": "R. Barata Ribeiro, 391", "hours": "6h-22h"},
    
    # Brasilia (2 unidades)
    {"id": 7, "code": "bsb-sudoeste", "name": "Brasilia - Sudoeste", "address": "CCSW 01 Lote 04", "hours": "24h"},
    {"id": 8, "code": "bsb-asa-sul", "name": "Brasilia - Asa Sul", "address": "SHS Quadra 1 Bloco A - Galeria Hotel Nacional", "hours": "24h"}
]

bookings_db = []

# Availability database - structure: {user_id: {date: {status, time_slots}}}
availability_db = {}

services_db = [
    {"id": 1, "name": "Shiatsu", "duration": 60, "price": 120.0},
    {"id": 2, "name": "Relaxante", "duration": 60, "price": 100.0},
    {"id": 3, "name": "Quick Massage", "duration": 15, "price": 40.0},
    {"id": 4, "name": "Terapeutica", "duration": 75, "price": 150.0}
]

# ============================================================================
# FUNÇÕES UTILITÁRIAS
# ============================================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_access_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str) -> Dict:
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token invalido")
        
        # Find user in database
        user = next((u for u in users_db if u["id"] == user_id), None)
        if user is None:
            raise HTTPException(status_code=401, detail="Usuario nao encontrado")
        
        return user
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except DecodeError:
        raise HTTPException(status_code=401, detail="Token invalido")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro na validacao do token: {str(e)}")

def get_next_id(table: List) -> int:
    return max([item["id"] for item in table], default=0) + 1

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
            "users": len(users_db),
            "bookings": len(bookings_db),
            "units": len(units_db),
            "services": len(services_db)
        }
    }

# AUTH
@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    print(f"Dados recebidos para registro: {user_data}")
    print(f"Especialidades: {user_data.specialties}")
    print(f"Precos especialidades: {user_data.specialty_prices}")
    errors = []
    
    # Check if user already exists
    if any(u["email"] == user_data.email for u in users_db):
        errors.append("E-mail ja esta cadastrado")
    
    # Validate CPF if provided
    if user_data.cpf:
        if not validate_cpf(user_data.cpf):
            errors.append("CPF invalido")
        elif any(u.get("cpf") == user_data.cpf for u in users_db):
            errors.append("CPF ja esta cadastrado")
    
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
    
    new_user = {
        "id": get_next_id(users_db),
        "name": user_data.name.strip(),
        "email": user_data.email.lower(),
        "password": hash_password(user_data.password),
        "cpf": user_data.cpf,
        "phone": user_data.phone,
        "unit_preference": user_data.unit_preference,
        "specialties": user_data.specialties,
        "specialty_prices": [sp.dict() for sp in user_data.specialty_prices],
        "birth_date": user_data.birth_date,
        "gender": user_data.gender,
        "experience_years": user_data.experience_years,
        "is_available": True,
        "user_type": "massagista",
        "created_at": datetime.now().isoformat()
    }
    
    users_db.append(new_user)
    print(f"Usuario salvo no banco: {new_user}")
    print(f"Especialidades salvas: {new_user.get('specialties', [])}")
    print(f"Precos salvos: {new_user.get('specialty_prices', [])}")
    return {"message": "Usuario cadastrado com sucesso", "user_id": new_user["id"]}

@app.post("/api/auth/login")
async def login(login_data: UserLogin):
    user = next((u for u in users_db if u["email"] == login_data.email), None)
    
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha invalidos")
    
    access_token = create_access_token(user["id"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "unit_preference": user["unit_preference"],
            "specialties": user.get("specialties", []),
            "specialty_prices": user.get("specialty_prices", [])
        }
    }

@app.get("/api/auth/me")
async def get_current_user(authorization: str = Header(None)):
    """Get current user information from JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Token de autorizacao nao fornecido")
    
    # Extract token from Authorization header (format: "Bearer <token>")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Formato de token inválido")
    
    token = authorization.split(" ")[1]
    user = verify_access_token(token)
    
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "unit_preference": user["unit_preference"],
        "specialties": user.get("specialties", []),
        "specialty_prices": user.get("specialty_prices", []),
        "massage_types": ", ".join(user.get("specialties", [])),
        "phone": user.get("phone", ""),
        "is_online": True
    }

# UNITS
@app.get("/api/units")
async def get_units():
    return units_db

# MASSAGISTAS
@app.get("/api/massagista/by-unit/{unit_code}")
async def get_massagistas_by_unit(unit_code: str):
    print(f"Buscando massagistas para unidade: {unit_code}")
    print(f"Total usuários no banco: {len(users_db)}")
    
    unit = next((u for u in units_db if u["code"] == unit_code), None)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    
    # Debug users
    for u in users_db:
        print(f"User: {u['name']}, type: {u.get('user_type')}, unit: {u.get('unit_preference')}, available: {u.get('is_available')}")
    
    massagistas = [
        {
            "id": u["id"],
            "name": u["name"],
            "specialties": u.get("specialties", []),
            "specialty_prices": u.get("specialty_prices", []),
            "is_available": u.get("is_available", True),
            "avatar_url": "/static/assets/images/default-avatar.png"
        }
        for u in users_db 
        if u["user_type"] == "massagista" 
        and u.get("unit_preference") == unit_code 
        and u.get("is_available", True)
    ]
    
    print(f"Massagistas encontradas: {len(massagistas)}")
    return massagistas

# BOOKINGS
@app.post("/api/bookings")
async def create_booking(booking_data: BookingCreate):
    unit = next((u for u in units_db if u["code"] == booking_data.unit_code), None)
    if not unit:
        raise HTTPException(status_code=400, detail="Unidade não encontrada")
    
    massagista = next((u for u in users_db if u["id"] == booking_data.massagista_id), None)
    if not massagista:
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
    massagista = next((u for u in users_db if u["id"] == massagista_id), None)
    if not massagista:
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
async def forgot_password(request: ForgotPasswordRequest):
    user = next((u for u in users_db if u["email"] == request.email), None)
    
    if not user:
        return {"message": "Se o email existir em nosso sistema, voce recebera instrucoes de redefinicao."}
    
    reset_token = secrets.token_urlsafe(6)[:6].upper()
    reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    user["reset_token"] = reset_token
    user["reset_token_expires"] = reset_expires
    
    # Try to send the email
    email_sent = send_password_reset_email(request.email, reset_token)
    
    # Always return the same message for security (don't reveal if email exists)
    return {
        "message": "Se o email existir em nosso sistema, voce recebera um codigo de verificacao.",
        "details": "Verifique sua caixa de entrada e spam. O codigo expira em 1 hora."
    }

@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = next((u for u in users_db 
                if u.get("reset_token") == request.token.upper() 
                and u.get("reset_token_expires") 
                and u["reset_token_expires"] > datetime.utcnow()), None)
    
    if not user:
        raise HTTPException(status_code=400, detail="Token invalido ou expirado")
    
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")
    
    user["password"] = hash_password(request.new_password)
    user["reset_token"] = None
    user["reset_token_expires"] = None
    
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
            massagista = next((u for u in users_db if u["id"] == booking["massagista_id"]), None)
            massagista_name = massagista["name"] if massagista else None
        
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
async def get_today_appointments():
    try:
        user_id = 1
        today = datetime.now().date()
        
        today_bookings = []
        for b in bookings_db:
            # Convert appointment_date to date object for comparison
            appointment_date = b.get("appointment_date")
            if isinstance(appointment_date, str):
                appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            
            if b.get("massagista_id") == user_id and appointment_date == today:
                # Convert date to string for JSON serialization
                booking_copy = b.copy()
                if isinstance(booking_copy.get("appointment_date"), date):
                    booking_copy["appointment_date"] = booking_copy["appointment_date"].isoformat()
                if isinstance(booking_copy.get("created_at"), datetime):
                    booking_copy["created_at"] = booking_copy["created_at"].isoformat()
                today_bookings.append(booking_copy)
        
        print(f"Agendamentos hoje para user {user_id}: {len(today_bookings)}")
        return today_bookings
    except Exception as e:
        print(f"ERRO Today Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/week")
async def get_week_appointments():
    try:
        user_id = 1
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        week_bookings = []
        for b in bookings_db:
            appointment_date = b.get("appointment_date")
            if isinstance(appointment_date, str):
                appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            
            if b.get("massagista_id") == user_id and start_of_week <= appointment_date <= end_of_week:
                booking_copy = b.copy()
                if isinstance(booking_copy.get("appointment_date"), date):
                    booking_copy["appointment_date"] = booking_copy["appointment_date"].isoformat()
                if isinstance(booking_copy.get("created_at"), datetime):
                    booking_copy["created_at"] = booking_copy["created_at"].isoformat()
                week_bookings.append(booking_copy)
        
        print(f"Agendamentos desta semana para user {user_id}: {len(week_bookings)}")
        return week_bookings
    except Exception as e:
        print(f"ERRO Week Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/month")
async def get_month_appointments():
    try:
        user_id = 1
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        next_month = start_of_month.replace(month=start_of_month.month % 12 + 1) if start_of_month.month < 12 else start_of_month.replace(year=start_of_month.year + 1, month=1)
        end_of_month = next_month - timedelta(days=1)
        
        month_bookings = []
        for b in bookings_db:
            appointment_date = b.get("appointment_date")
            if isinstance(appointment_date, str):
                appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
            
            if b.get("massagista_id") == user_id and start_of_month <= appointment_date <= end_of_month:
                booking_copy = b.copy()
                if isinstance(booking_copy.get("appointment_date"), date):
                    booking_copy["appointment_date"] = booking_copy["appointment_date"].isoformat()
                if isinstance(booking_copy.get("created_at"), datetime):
                    booking_copy["created_at"] = booking_copy["created_at"].isoformat()
                month_bookings.append(booking_copy)
        
        print(f"Agendamentos deste mês para user {user_id}: {len(month_bookings)}")
        return month_bookings
    except Exception as e:
        print(f"ERRO Month Appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/massagista/appointments/all")
async def get_all_appointments():
    try:
        user_id = 1
        
        all_bookings = []
        for b in bookings_db:
            if b.get("massagista_id") == user_id:
                booking_copy = b.copy()
                if isinstance(booking_copy.get("appointment_date"), date):
                    booking_copy["appointment_date"] = booking_copy["appointment_date"].isoformat()
                if isinstance(booking_copy.get("created_at"), datetime):
                    booking_copy["created_at"] = booking_copy["created_at"].isoformat()
                all_bookings.append(booking_copy)
        
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
async def get_day_availability(date: str, authorization: str = Header(None)):
    """Get availability for a specific day"""
    user = verify_access_token(authorization.split(" ")[1] if authorization else "")
    user_id = user["id"]
    
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
async def get_month_availability(year: int, month: int, authorization: str = Header(None)):
    """Get availability for entire month"""
    user = verify_access_token(authorization.split(" ")[1] if authorization else "")
    user_id = user["id"]
    
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