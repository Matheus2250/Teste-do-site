from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import hashlib
import jwt
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import calendar as cal
from collections import defaultdict

app = FastAPI(
    title="Espaço VIV API - Render",
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

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    cpf: Optional[str] = None
    phone: Optional[str] = None
    unit_preference: Optional[str] = None
    specialties: List[str] = []
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

class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialties: Optional[List[str]] = None
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

users_db = [
    {
        "id": 1, "name": "Ana Silva", "email": "ana@espacoviv.com", 
        "password": hashlib.sha256("123456".encode()).hexdigest(),
        "cpf": "111.111.111-11", "phone": "(11) 99999-1111",
        "unit_preference": "sp-perdizes", "specialties": ["Shiatsu", "Relaxante"],
        "is_available": True, "user_type": "massagista"
    },
    {
        "id": 2, "name": "Maria Santos", "email": "maria@espacoviv.com",
        "password": hashlib.sha256("123456".encode()).hexdigest(),
        "cpf": "222.222.222-22", "phone": "(11) 99999-2222",
        "unit_preference": "rj-centro", "specialties": ["Quick", "Terapêutica"],
        "is_available": True, "user_type": "massagista"
    }
]

units_db = [
    {"id": 1, "code": "sp-perdizes", "name": "São Paulo - Perdizes", "address": "Rua da Consolação, 123"},
    {"id": 2, "code": "sp-vila-clementino", "name": "São Paulo - Vila Clementino", "address": "Av. Domingos de Morais, 456"},
    {"id": 3, "code": "rj-centro", "name": "Rio de Janeiro - Centro", "address": "Av. Rio Branco, 200"},
    {"id": 4, "code": "bsb-sudoeste", "name": "Brasília - Sudoeste", "address": "SHS Quadra 6"}
]

bookings_db = []

services_db = [
    {"id": 1, "name": "Shiatsu", "duration": 60, "price": 120.0},
    {"id": 2, "name": "Relaxante", "duration": 60, "price": 100.0},
    {"id": 3, "name": "Quick Massage", "duration": 15, "price": 40.0},
    {"id": 4, "name": "Terapêutica", "duration": 75, "price": 150.0}
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
    """Send password reset email"""
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    
    if not all([smtp_user, smtp_password]):
        print(f"⚠️ Email não configurado. Reset token para {email}: {reset_token}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = "Espaço VIV - Redefinir Senha"
        
        html_body = f"""
        <html>
        <body>
            <h2>🌿 Espaço VIV - Redefinição de Senha</h2>
            <p>Olá!</p>
            <p>Você solicitou a redefinição da sua senha. Use o código abaixo:</p>
            <div style="background-color: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                <h3 style="color: #2c5530; font-family: monospace; letter-spacing: 2px;">{reset_token}</h3>
            </div>
            <p>Este código é válido por 1 hora.</p>
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
        "message": "🚀 Espaço VIV API no Render funcionando!",
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production"),
        "database": "in-memory (temporário)"
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
    errors = []
    
    # Check if user already exists
    if any(u["email"] == user_data.email for u in users_db):
        errors.append("E-mail já está cadastrado")
    
    # Validate CPF if provided
    if user_data.cpf:
        if not validate_cpf(user_data.cpf):
            errors.append("CPF inválido")
        elif any(u.get("cpf") == user_data.cpf for u in users_db):
            errors.append("CPF já está cadastrado")
    
    # Validate password strength
    password_validation = validate_password_strength(user_data.password)
    if not password_validation["is_valid"]:
        errors.extend(password_validation["errors"][:2])
    
    # Validate name
    if len(user_data.name.strip()) < 2:
        errors.append("Nome deve ter pelo menos 2 caracteres")
    
    # Validate phone format
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
        "birth_date": user_data.birth_date,
        "gender": user_data.gender,
        "experience_years": user_data.experience_years,
        "is_available": True,
        "user_type": "massagista",
        "created_at": datetime.now().isoformat()
    }
    
    users_db.append(new_user)
    return {"message": "Usuário cadastrado com sucesso", "user_id": new_user["id"]}

@app.post("/api/auth/login")
async def login(login_data: UserLogin):
    user = next((u for u in users_db if u["email"] == login_data.email), None)
    
    if not user or not verify_password(login_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")
    
    access_token = create_access_token(user["id"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "unit_preference": user["unit_preference"]
        }
    }

# UNITS
@app.get("/api/units")
async def get_units():
    return units_db

# MASSAGISTAS
@app.get("/api/massagista/by-unit/{unit_code}")
async def get_massagistas_by_unit(unit_code: str):
    unit = next((u for u in units_db if u["code"] == unit_code), None)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    
    massagistas = [
        {
            "id": u["id"],
            "name": u["name"],
            "specialties": u.get("specialties", []),
            "is_available": u.get("is_available", True),
            "avatar_url": "/static/assets/images/default-avatar.png"
        }
        for u in users_db 
        if u["user_type"] == "massagista" 
        and u.get("unit_preference") == unit_code 
        and u.get("is_available", True)
    ]
    
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
        
        base_times = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
        
        # Remove horários ocupados
        booked_times = [
            b["appointment_time"] for b in bookings_db 
            if b["massagista_id"] == massagista_id and b["appointment_date"] == appointment_date
            and b["status"] in ["pending", "confirmed"]
        ]
        
        available = [t for t in base_times if t not in booked_times]
        return available
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

# FORGOT PASSWORD
@app.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    user = next((u for u in users_db if u["email"] == request.email), None)
    
    if not user:
        return {"message": "Se o email existir em nosso sistema, você receberá instruções de redefinição."}
    
    reset_token = secrets.token_urlsafe(6)[:6].upper()
    reset_expires = datetime.utcnow() + timedelta(hours=1)
    
    user["reset_token"] = reset_token
    user["reset_token_expires"] = reset_expires
    
    email_sent = send_password_reset_email(request.email, reset_token)
    
    if not email_sent:
        print(f"🔑 Reset token para {request.email}: {reset_token}")
    
    return {"message": "Se o email existir em nosso sistema, você receberá instruções de redefinição."}

@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest):
    user = next((u for u in users_db 
                if u.get("reset_token") == request.token.upper() 
                and u.get("reset_token_expires") 
                and u["reset_token_expires"] > datetime.utcnow()), None)
    
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")
    
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter pelo menos 6 caracteres")
    
    user["password"] = hash_password(request.new_password)
    user["reset_token"] = None
    user["reset_token_expires"] = None
    
    return {"message": "Senha redefinida com sucesso! Você já pode fazer login."}

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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)