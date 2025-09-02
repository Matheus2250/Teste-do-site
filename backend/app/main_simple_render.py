from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, timedelta
import hashlib
import jwt
import os

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
        "user_type": "massagista"
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

# SERVICES
@app.get("/api/services")
async def get_services():
    return services_db

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)