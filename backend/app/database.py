import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://espacoviv_user:your_secure_password@localhost/espacoviv_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    from app.models import Base
    Base.metadata.create_all(bind=engine)

def init_db():
    """Initialize database with default data"""
    from app.models import Unit, Service
    
    db = SessionLocal()
    try:
        # Check if units already exist
        if db.query(Unit).count() == 0:
            # Add default units
            units_data = [
                {
                    "name": "Espaco VIV - Asa Norte",
                    "address": "SQN 203 Bloco A, Loja 06 - Asa Norte, Brasilia - DF, 70832-010",
                    "description": "Nossa unidade da Asa Norte oferece um ambiente acolhedor e moderno, com profissionais especializados em diversas tecnicas de bem-estar e relaxamento.",
                    "image_url": "frontend/assets/images/brasilia-nova.jpg"
                },
                {
                    "name": "Espaco VIV - Sao Paulo",
                    "address": "Rua das Palmeiras, 123 - Vila Madalena, Sao Paulo - SP, 05422-000",
                    "description": "Nossa unidade em Sao Paulo combina tecnologia de ponta com um ambiente relaxante, proporcionando experiencias unicas de bem-estar no coracao da cidade.",
                    "image_url": "frontend/assets/images/sao-paulo-nova.jpg"
                },
                {
                    "name": "Espaco VIV - Rio de Janeiro",
                    "address": "Av. das Americas, 456 - Barra da Tijuca, Rio de Janeiro - RJ, 22640-100",
                    "description": "Localizada na Barra da Tijuca, nossa unidade do Rio oferece uma vista deslumbrante e tratamentos exclusivos em um ambiente tropical e aconchegante.",
                    "image_url": "frontend/assets/images/rio-nova.jpg"
                }
            ]
            
            for unit_data in units_data:
                unit = Unit(**unit_data)
                db.add(unit)
            
            db.commit()
            
            # Add default services for each unit
            services_data = [
                {"name": "Massagem Relaxante", "description": "Massagem suave para aliviar tensoes e promover relaxamento", "price": 80.0, "duration_minutes": 60},
                {"name": "Massagem Terapeutica", "description": "Massagem focada em aliviar dores musculares e melhorar a circulacao", "price": 100.0, "duration_minutes": 75},
                {"name": "Drenagem Linfatica", "description": "Tecnica especializada para reducao de inchacos e melhora da circulacao linfatica", "price": 90.0, "duration_minutes": 60},
                {"name": "Reflexologia", "description": "Massagem nos pes que estimula pontos reflexos para promover bem-estar geral", "price": 70.0, "duration_minutes": 45},
                {"name": "Acupuntura", "description": "Terapia milenar chinesa com agulhas para equilibrio energetico e alivio de dores", "price": 120.0, "duration_minutes": 60}
            ]
            
            units = db.query(Unit).all()
            for unit in units:
                for service_data in services_data:
                    service = Service(**service_data, unit_id=unit.id)
                    db.add(service)
            
            db.commit()
            print("[DATABASE] Dados iniciais criados com sucesso")
    
    except Exception as e:
        print(f"[DATABASE] Erro ao inicializar dados: {e}")
        db.rollback()
    finally:
        db.close()