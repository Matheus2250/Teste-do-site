"""
Espaço VIV - FastAPI Application para Render
"""
import sys
import os
from pathlib import Path

# Adicionar o diretório backend ao Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

# Configurar variáveis de ambiente para produção
os.environ.setdefault("ENVIRONMENT", "production")

# Importar a aplicação
try:
    from app.main_simple_render import app
    print("✅ Aplicação Render carregada com sucesso!")
except ImportError as e:
    print(f"❌ Erro ao importar aplicação: {e}")
    # Fallback para aplicação de emergência
    from fastapi import FastAPI
    
    app = FastAPI(title="Espaço VIV - Emergency Mode")
    
    @app.get("/")
    def root():
        return {"message": "Espaço VIV API em modo de emergência", "status": "ok"}
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "mode": "emergency"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))  # Render usa porta 10000 por padrão
    uvicorn.run(app, host="0.0.0.0", port=port)