from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from database.connection import get_db
from models.users import Unit

router = APIRouter()

# Pydantic models
class UnitInfo(BaseModel):
    id: int
    code: str
    name: str
    city: str
    state: str
    address: str
    phone: Optional[str]
    email: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True

class UnitCreate(BaseModel):
    code: str
    name: str
    city: str
    state: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None

@router.get("/", response_model=List[UnitInfo])
async def get_all_units(db: Session = Depends(get_db)):
    units = db.query(Unit).filter(Unit.is_active == True).order_by(Unit.name).all()
    return [UnitInfo.from_orm(unit) for unit in units]

@router.get("/{unit_code}", response_model=UnitInfo)
async def get_unit_by_code(unit_code: str, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(
        Unit.code == unit_code,
        Unit.is_active == True
    ).first()
    
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    return UnitInfo.from_orm(unit)

@router.post("/", response_model=UnitInfo)
async def create_unit(unit_data: UnitCreate, db: Session = Depends(get_db)):
    # Check if unit code already exists
    existing_unit = db.query(Unit).filter(Unit.code == unit_data.code).first()
    if existing_unit:
        raise HTTPException(
            status_code=400,
            detail="Unit code already exists"
        )
    
    # Create new unit
    new_unit = Unit(
        code=unit_data.code,
        name=unit_data.name,
        city=unit_data.city,
        state=unit_data.state,
        address=unit_data.address,
        phone=unit_data.phone,
        email=unit_data.email
    )
    
    db.add(new_unit)
    db.commit()
    db.refresh(new_unit)
    
    return UnitInfo.from_orm(new_unit)