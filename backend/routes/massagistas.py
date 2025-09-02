from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

from database.connection import get_db
from models.users import User, MassagistaProfile, Unit
from models.bookings import Booking, BookingStatus
from utils.auth import get_current_user
from routes.bookings import BookingResponse

router = APIRouter()

# Pydantic models
class MassagistaInfo(BaseModel):
    id: int
    name: str
    specialties: Optional[List[str]] = []
    avatar_url: Optional[str] = None
    is_available: bool
    unit_preference: Optional[str] = None
    
    class Config:
        from_attributes = True

class MassagistaProfileUpdate(BaseModel):
    specialties: Optional[List[str]] = None
    bio: Optional[str] = None
    is_available: Optional[bool] = None
    working_hours: Optional[dict] = None

@router.get("/by-unit/{unit_code}", response_model=List[MassagistaInfo])
async def get_massagistas_by_unit(unit_code: str, db: Session = Depends(get_db)):
    # Get unit to validate
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    # Get massagistas for this unit
    massagistas = db.query(User).join(MassagistaProfile).filter(
        and_(
            User.user_type == "massagista",
            User.is_active == True,
            MassagistaProfile.is_available == True,
            or_(
                MassagistaProfile.unit_preference == unit_code,
                MassagistaProfile.unit_preference == None
            )
        )
    ).all()
    
    response = []
    for massagista in massagistas:
        profile = massagista.massagista_profile
        specialties = []
        if profile and profile.specialties:
            try:
                import json
                specialties = json.loads(profile.specialties)
            except:
                specialties = []
        
        response.append(MassagistaInfo(
            id=massagista.id,
            name=massagista.name,
            specialties=specialties,
            avatar_url=profile.avatar_url if profile else None,
            is_available=profile.is_available if profile else True,
            unit_preference=profile.unit_preference if profile else None
        ))
    
    return response

@router.get("/appointments", response_model=List[BookingResponse])
async def get_my_appointments(
    status: Optional[BookingStatus] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Booking).join(Unit).filter(Booking.massagista_id == current_user.id)
    
    # Apply filters
    if status:
        query = query.filter(Booking.status == status)
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(func.date(Booking.appointment_date) >= from_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(func.date(Booking.appointment_date) <= to_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")
    
    bookings = query.order_by(Booking.appointment_date.asc()).all()
    
    # Format response
    response = []
    for booking in bookings:
        response.append(BookingResponse(
            id=booking.id,
            client_name=booking.client_name,
            client_phone=booking.client_phone,
            service=booking.service,
            appointment_date=booking.appointment_date,
            appointment_time=booking.appointment_time,
            status=booking.status.value,
            notes=booking.notes,
            unit_name=booking.unit.name,
            massagista_name=current_user.name,
            created_at=booking.created_at
        ))
    
    return response

@router.get("/appointments/calendar")
async def get_calendar_appointments(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Default to current month/year if not provided
    if not month or not year:
        now = datetime.now()
        month = month or now.month
        year = year or now.year
    
    # Get appointments for the month
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    
    bookings = db.query(Booking).filter(
        and_(
            Booking.massagista_id == current_user.id,
            func.date(Booking.appointment_date) >= start_date,
            func.date(Booking.appointment_date) < end_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).all()
    
    # Group by date
    calendar_data = {}
    for booking in bookings:
        date_str = booking.appointment_date.date().isoformat()
        if date_str not in calendar_data:
            calendar_data[date_str] = []
        
        calendar_data[date_str].append({
            "id": booking.id,
            "client_name": booking.client_name,
            "service": booking.service,
            "time": booking.appointment_time,
            "status": booking.status.value
        })
    
    return calendar_data

@router.put("/appointments/{booking_id}/status", response_model=BookingResponse)
async def update_appointment_status(
    booking_id: int,
    status_update: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(
        and_(
            Booking.id == booking_id,
            Booking.massagista_id == current_user.id
        )
    ).first()
    
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found or not assigned to you"
        )
    
    # Validate status
    try:
        new_status = BookingStatus(status_update.get("status"))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )
    
    # Update status
    old_status = booking.status
    booking.status = new_status
    
    # Update timestamp fields
    if new_status == BookingStatus.CONFIRMED and old_status != BookingStatus.CONFIRMED:
        booking.confirmed_at = datetime.utcnow()
    elif new_status == BookingStatus.CANCELLED and old_status != BookingStatus.CANCELLED:
        booking.cancelled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(booking)
    
    return BookingResponse(
        id=booking.id,
        client_name=booking.client_name,
        client_phone=booking.client_phone,
        service=booking.service,
        appointment_date=booking.appointment_date,
        appointment_time=booking.appointment_time,
        status=booking.status.value,
        notes=booking.notes,
        unit_name=booking.unit.name,
        massagista_name=current_user.name,
        created_at=booking.created_at
    )

@router.get("/profile", response_model=dict)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(MassagistaProfile).filter(MassagistaProfile.user_id == current_user.id).first()
    
    if not profile:
        # Create default profile if it doesn't exist
        profile = MassagistaProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    specialties = []
    working_hours = {}
    
    if profile.specialties:
        try:
            import json
            specialties = json.loads(profile.specialties)
        except:
            pass
    
    if profile.working_hours:
        try:
            import json
            working_hours = json.loads(profile.working_hours)
        except:
            pass
    
    return {
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone
        },
        "profile": {
            "specialties": specialties,
            "unit_preference": profile.unit_preference,
            "bio": profile.bio,
            "avatar_url": profile.avatar_url,
            "is_available": profile.is_available,
            "working_hours": working_hours
        }
    }

@router.put("/profile", response_model=dict)
async def update_my_profile(
    profile_update: MassagistaProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    profile = db.query(MassagistaProfile).filter(MassagistaProfile.user_id == current_user.id).first()
    
    if not profile:
        profile = MassagistaProfile(user_id=current_user.id)
        db.add(profile)
    
    # Update profile fields
    if profile_update.specialties is not None:
        import json
        profile.specialties = json.dumps(profile_update.specialties)
    
    if profile_update.bio is not None:
        profile.bio = profile_update.bio
    
    if profile_update.is_available is not None:
        profile.is_available = profile_update.is_available
    
    if profile_update.working_hours is not None:
        import json
        profile.working_hours = json.dumps(profile_update.working_hours)
    
    db.commit()
    db.refresh(profile)
    
    return {"message": "Profile updated successfully"}