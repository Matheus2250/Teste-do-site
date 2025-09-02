from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from contextlib import asynccontextmanager

from database.connection import get_db, init_db
from routes import auth, bookings, massagistas, units
from utils.auth import get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Espaço VIV API",
    description="API para sistema de agendamento de massagens",
    version="1.0.0",
    lifespan=lifespan
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
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# API Routes
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(massagistas.router, prefix="/api/massagista", tags=["massagistas"])
app.include_router(units.router, prefix="/api/units", tags=["units"])

@app.get("/")
async def root():
    return {"message": "Espaço VIV API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)