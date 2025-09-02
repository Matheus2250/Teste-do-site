from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(
    title="Espaço VIV API - Versão Simples",
    description="API para sistema de agendamento de massagens (sem banco de dados)",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
async def root():
    return {"message": "Espaço VIV API está funcionando!", "status": "success"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# Rotas de teste para o frontend
@app.get("/api/units")
async def get_units():
    return [
        {"id": 1, "code": "SP", "name": "São Paulo", "address": "Rua da Consolação, 123"},
        {"id": 2, "code": "RJ", "name": "Rio de Janeiro", "address": "Av. Rio Branco, 456"},
        {"id": 3, "code": "BSB", "name": "Brasília", "address": "SHS Quadra 6, Bloco A"}
    ]

@app.get("/api/massagista/by-unit/{unit_code}")
async def get_massagistas_by_unit(unit_code: str):
    massagistas = {
        "SP": [
            {"id": 1, "name": "Ana Silva", "specialties": ["Relaxante", "Shiatsu"], "is_available": True},
            {"id": 2, "name": "Maria Santos", "specialties": ["Quick Massage", "Drenagem"], "is_available": True}
        ],
        "RJ": [
            {"id": 3, "name": "João Costa", "specialties": ["Relaxante", "Pedras Quentes"], "is_available": True},
            {"id": 4, "name": "Paula Lima", "specialties": ["Shiatsu", "Ventosa"], "is_available": True}
        ],
        "BSB": [
            {"id": 5, "name": "Carlos Oliveira", "specialties": ["Quick Massage", "Relaxante"], "is_available": True},
            {"id": 6, "name": "Fernanda Souza", "specialties": ["Drenagem", "Redutora"], "is_available": True}
        ]
    }
    return massagistas.get(unit_code, [])

@app.post("/api/bookings")
async def create_booking(booking_data: dict):
    return {
        "id": 123,
        "message": "Agendamento criado com sucesso!",
        "status": "pending",
        "data": booking_data
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)