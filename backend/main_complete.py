from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
import jwt
import hashlib
import os
from dataclasses import dataclass
import json

app = FastAPI(
    title="Espaço VIV API Completa",
    description="API completa para sistema de agendamento de massagens",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()
SECRET_KEY = "espaco-viv-secret-key-2024"
ALGORITHM = "HS256"

# Static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    cpf: Optional[str] = None
    phone: Optional[str] = None
    unit_preference: Optional[str] = None
    specialties: List[str] = []

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
    promotion: Optional[str] = None

class BookingUpdate(BaseModel):
    status: str

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    specialties: List[str] = []
    is_available: Optional[bool] = None

# ============================================================================
# BANCO DE DADOS EM MEMÓRIA (MOCK)
# ============================================================================

# Usuários (Massagistas)
users_db = [
    {
        "id": 1, "name": "Ana Silva", "email": "ana@espacoviv.com", 
        "password": hashlib.sha256("123456".encode()).hexdigest(),
        "cpf": "111.111.111-11", "phone": "(11) 99999-1111",
        "unit_preference": "sp-perdizes", "specialties": ["Shiatsu", "Relaxante"],
        "is_available": True, "user_type": "massagista", "created_at": datetime.now()
    },
    {
        "id": 2, "name": "Maria Santos", "email": "maria@espacoviv.com",
        "password": hashlib.sha256("123456".encode()).hexdigest(),
        "cpf": "222.222.222-22", "phone": "(11) 99999-2222",
        "unit_preference": "sp-vila-clementino", "specialties": ["Quick", "Terapêutica"],
        "is_available": True, "user_type": "massagista", "created_at": datetime.now()
    },
    {
        "id": 3, "name": "João Costa", "email": "joao@espacoviv.com",
        "password": hashlib.sha256("123456".encode()).hexdigest(),
        "cpf": "333.333.333-33", "phone": "(21) 99999-3333",
        "unit_preference": "rj-centro", "specialties": ["Relaxante", "Pedras Quentes"],
        "is_available": True, "user_type": "massagista", "created_at": datetime.now()
    }
]

# Unidades
units_db = [
    {"id": 1, "code": "sp-perdizes", "name": "São Paulo - Perdizes", "address": "Rua da Consolação, 123"},
    {"id": 2, "code": "sp-vila-clementino", "name": "São Paulo - Vila Clementino", "address": "Av. Domingos de Morais, 456"},
    {"id": 3, "code": "sp-ingleses", "name": "São Paulo - Ingleses", "address": "Rua Augusta, 789"},
    {"id": 4, "code": "sp-prudente", "name": "São Paulo - Prudente", "address": "Av. Paulista, 1000"},
    {"id": 5, "code": "rj-centro", "name": "Rio de Janeiro - Centro", "address": "Av. Rio Branco, 200"},
    {"id": 6, "code": "rj-copacabana", "name": "Rio de Janeiro - Copacabana", "address": "Av. Atlântica, 500"},
    {"id": 7, "code": "bsb-sudoeste", "name": "Brasília - Sudoeste", "address": "SHS Quadra 6"},
    {"id": 8, "code": "bsb-asa-sul", "name": "Brasília - Asa Sul", "address": "Galeria Hotel Nacional"}
]

# Agendamentos
bookings_db = [
    {
        "id": 1, "client_name": "Carlos Silva", "client_phone": "(11) 99999-0001",
        "unit_code": "sp-perdizes", "massagista_id": 1, "service": "Shiatsu",
        "appointment_date": date.today(), "appointment_time": "09:00",
        "status": "confirmed", "notes": "Primeira vez", "created_at": datetime.now()
    },
    {
        "id": 2, "client_name": "Laura Santos", "client_phone": "(11) 99999-0002",
        "unit_code": "sp-perdizes", "massagista_id": 1, "service": "Relaxante",
        "appointment_date": date.today(), "appointment_time": "14:30",
        "status": "pending", "notes": "", "created_at": datetime.now()
    }
]

# Serviços
services_db = [
    {"id": 1, "name": "Shiatsu", "duration": 60, "price": 120.0},
    {"id": 2, "name": "Relaxante", "duration": 60, "price": 100.0},
    {"id": 3, "name": "Quick Massage", "duration": 15, "price": 40.0},
    {"id": 4, "name": "Terapêutica", "duration": 75, "price": 150.0},
    {"id": 5, "name": "Drenagem Linfática", "duration": 90, "price": 180.0},
    {"id": 6, "name": "Pedras Quentes", "duration": 80, "price": 160.0},
    {"id": 7, "name": "Ventosaterapia", "duration": 45, "price": 80.0}
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

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user = next((u for u in users_db if u["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido")
        return user
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_available_times(date_str: str, massagista_id: int) -> List[str]:
    """Gera horários disponíveis para uma data e massagista"""
    base_times = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
    
    # Remove horários já ocupados
    appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    booked_times = [
        b["appointment_time"] for b in bookings_db 
        if b["massagista_id"] == massagista_id and b["appointment_date"] == appointment_date
        and b["status"] in ["pending", "confirmed"]
    ]
    
    available = [t for t in base_times if t not in booked_times]
    return available

def get_next_id(table: List[Dict]) -> int:
    return max([item["id"] for item in table], default=0) + 1

# ============================================================================
# ROTAS DE AUTENTICAÇÃO
# ============================================================================

@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    # Verificar se email já existe
    if any(u["email"] == user_data.email for u in users_db):
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")
    
    new_user = {
        "id": get_next_id(users_db),
        "name": user_data.name,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "cpf": user_data.cpf,
        "phone": user_data.phone,
        "unit_preference": user_data.unit_preference,
        "specialties": user_data.specialties,
        "is_available": True,
        "user_type": "massagista",
        "created_at": datetime.now()
    }
    
    users_db.append(new_user)
    
    return {
        "message": "Usuário cadastrado com sucesso",
        "user_id": new_user["id"]
    }

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

@app.post("/api/auth/forgot-password")
async def forgot_password(reset_data: PasswordReset):
    user = next((u for u in users_db if u["email"] == reset_data.email), None)
    if not user:
        # Por segurança, sempre retorna sucesso
        return {"message": "Se o e-mail estiver cadastrado, você receberá as instruções"}
    
    # Em produção, enviaria e-mail com token
    reset_token = create_access_token(user["id"])
    
    return {
        "message": "Instruções enviadas para seu e-mail",
        "reset_token": reset_token  # Em produção, isso não seria retornado aqui
    }

@app.post("/api/auth/reset-password")
async def reset_password(reset_data: PasswordResetConfirm):
    try:
        payload = jwt.decode(reset_data.token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user = next((u for u in users_db if u["id"] == user_id), None)
        if not user:
            raise HTTPException(status_code=400, detail="Token inválido")
        
        user["password"] = hash_password(reset_data.new_password)
        return {"message": "Senha alterada com sucesso"}
        
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

@app.get("/api/auth/me")
async def get_current_user_info(current_user = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "name": current_user["name"],
        "email": current_user["email"],
        "phone": current_user.get("phone"),
        "unit_preference": current_user.get("unit_preference"),
        "specialties": current_user.get("specialties", []),
        "is_available": current_user.get("is_available", True)
    }

# ============================================================================
# ROTAS DE UNIDADES
# ============================================================================

@app.get("/api/units")
async def get_units():
    return units_db

@app.get("/api/units/{unit_code}")
async def get_unit_by_code(unit_code: str):
    unit = next((u for u in units_db if u["code"] == unit_code), None)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    return unit

# ============================================================================
# ROTAS DE MASSAGISTAS
# ============================================================================

@app.get("/api/massagista/by-unit/{unit_code}")
async def get_massagistas_by_unit(unit_code: str):
    # Verificar se unidade existe
    unit = next((u for u in units_db if u["code"] == unit_code), None)
    if not unit:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")
    
    massagistas = [
        {
            "id": u["id"],
            "name": u["name"],
            "specialties": u.get("specialties", []),
            "is_available": u.get("is_available", True),
            "avatar_url": f"../assets/images/default-avatar.png"
        }
        for u in users_db 
        if u["user_type"] == "massagista" 
        and u.get("unit_preference") == unit_code 
        and u.get("is_available", True)
    ]
    
    return massagistas

@app.get("/api/massagista/appointments")
async def get_my_appointments(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    appointments = [
        b for b in bookings_db 
        if b["massagista_id"] == current_user["id"]
    ]
    
    # Filtros
    if status:
        appointments = [a for a in appointments if a["status"] == status]
    
    if date_from:
        from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        appointments = [a for a in appointments if a["appointment_date"] >= from_date]
    
    if date_to:
        to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        appointments = [a for a in appointments if a["appointment_date"] <= to_date]
    
    # Adicionar informações da unidade
    for appointment in appointments:
        unit = next((u for u in units_db if u["code"] == appointment["unit_code"]), None)
        appointment["unit_name"] = unit["name"] if unit else "Unidade não encontrada"
        appointment["massagista_name"] = current_user["name"]
    
    return sorted(appointments, key=lambda x: (x["appointment_date"], x["appointment_time"]))

@app.get("/api/massagista/appointments/calendar")
async def get_calendar_appointments(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user = Depends(get_current_user)
):
    now = datetime.now()
    month = month or now.month
    year = year or now.year
    
    # Obter agendamentos do mês
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    appointments = [
        b for b in bookings_db 
        if b["massagista_id"] == current_user["id"]
        and start_date <= b["appointment_date"] < end_date
        and b["status"] in ["pending", "confirmed"]
    ]
    
    # Agrupar por data
    calendar_data = {}
    for appointment in appointments:
        date_str = appointment["appointment_date"].isoformat()
        if date_str not in calendar_data:
            calendar_data[date_str] = []
        
        calendar_data[date_str].append({
            "id": appointment["id"],
            "client_name": appointment["client_name"],
            "service": appointment["service"],
            "time": appointment["appointment_time"],
            "status": appointment["status"]
        })
    
    return calendar_data

@app.put("/api/massagista/appointments/{booking_id}/status")
async def update_appointment_status(
    booking_id: int,
    status_update: BookingUpdate,
    current_user = Depends(get_current_user)
):
    booking = next((b for b in bookings_db if b["id"] == booking_id and b["massagista_id"] == current_user["id"]), None)
    if not booking:
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    
    if status_update.status not in ["pending", "confirmed", "cancelled", "completed", "no_show"]:
        raise HTTPException(status_code=400, detail="Status inválido")
    
    booking["status"] = status_update.status
    booking["updated_at"] = datetime.now()
    
    return {"message": "Status atualizado com sucesso", "booking": booking}

# ============================================================================
# ROTAS DE AGENDAMENTOS
# ============================================================================

@app.post("/api/bookings")
async def create_booking(booking_data: BookingCreate):
    # Verificar se unidade existe
    unit = next((u for u in units_db if u["code"] == booking_data.unit_code), None)
    if not unit:
        raise HTTPException(status_code=400, detail="Unidade não encontrada")
    
    # Verificar se massagista existe
    massagista = next((u for u in users_db if u["id"] == booking_data.massagista_id), None)
    if not massagista:
        raise HTTPException(status_code=400, detail="Massagista não encontrada")
    
    # Verificar disponibilidade do horário
    existing_booking = next((
        b for b in bookings_db 
        if b["massagista_id"] == booking_data.massagista_id
        and b["appointment_date"] == booking_data.appointment_date
        and b["appointment_time"] == booking_data.appointment_time
        and b["status"] in ["pending", "confirmed"]
    ), None)
    
    if existing_booking:
        raise HTTPException(status_code=400, detail="Horário não disponível")
    
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
        "promotion": booking_data.promotion,
        "created_at": datetime.now()
    }
    
    bookings_db.append(new_booking)
    
    return {
        "message": "Agendamento criado com sucesso",
        "booking_id": new_booking["id"],
        "status": "pending"
    }

@app.get("/api/bookings/available-times/{massagista_id}/{date}")
async def get_available_times_endpoint(massagista_id: int, date: str):
    # Verificar se massagista existe
    massagista = next((u for u in users_db if u["id"] == massagista_id), None)
    if not massagista:
        raise HTTPException(status_code=404, detail="Massagista não encontrada")
    
    try:
        # Validar formato da data
        appointment_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Não permitir agendamentos no passado
        if appointment_date < datetime.now().date():
            return []
        
        available_times = get_available_times(date, massagista_id)
        return available_times
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD")

# ============================================================================
# ROTAS DE SERVIÇOS
# ============================================================================

@app.get("/api/services")
async def get_services():
    return services_db

# ============================================================================
# ROTAS DE PERFIL
# ============================================================================

@app.put("/api/profile")
async def update_profile(
    profile_data: ProfileUpdate,
    current_user = Depends(get_current_user)
):
    user = next((u for u in users_db if u["id"] == current_user["id"]), None)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if profile_data.name:
        user["name"] = profile_data.name
    if profile_data.phone:
        user["phone"] = profile_data.phone
    if profile_data.specialties:
        user["specialties"] = profile_data.specialties
    if profile_data.is_available is not None:
        user["is_available"] = profile_data.is_available
    
    user["updated_at"] = datetime.now()
    
    return {"message": "Perfil atualizado com sucesso"}

# ============================================================================
# ROTAS PRINCIPAIS
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Espaço VIV API Completa está funcionando!",
        "status": "success",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "auth": "/api/auth/*",
            "units": "/api/units",
            "massagistas": "/api/massagista/*",
            "bookings": "/api/bookings",
            "services": "/api/services"
        }
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)