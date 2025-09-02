from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
from contextlib import asynccontextmanager

# Imports dos modelos e rotas originais
from database.connection import get_db, init_db
from routes import auth, bookings, massagistas, units
from utils.auth import get_current_user

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - inicializar banco
    try:
        init_db()
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Espaço VIV API - Produção",
    description="API para sistema de agendamento de massagens",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None
)

# CORS configuration - mais restritivo em produção
ALLOWED_ORIGINS = [
    "https://espacoviv.onrender.com",
    "https://espacoviv.com", 
    "https://www.espacoviv.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]

if os.getenv("ENVIRONMENT") == "development":
    ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files para produção
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
    return {
        "message": "Espaço VIV API está funcionando!",
        "status": "healthy",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "production")
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Teste de conexão com o banco
        db.execute("SELECT 1")
        database_status = "connected"
    except:
        database_status = "disconnected"
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": database_status,
        "environment": os.getenv("ENVIRONMENT", "production")
    }

# Root redirect para documentação em desenvolvimento
if os.getenv("ENVIRONMENT") == "development":
    from fastapi.responses import RedirectResponse
    
    @app.get("/admin")
    async def admin_redirect():
        return RedirectResponse(url="/docs")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)