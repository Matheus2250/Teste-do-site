from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, date, time
import json

from database.connection import get_db
from models.bookings import Booking, BookingStatus, Availability
from models.users import User, Unit
from utils.auth import get_current_user

router = APIRouter()

# Pydantic models
class BookingCreate(BaseModel):
    client_name: str
    client_email: Optional[EmailStr] = None
    client_phone: str
    service: str
    appointment_date: str  # YYYY-MM-DD format
    appointment_time: str  # HH:MM format
    unit_id: str  # Unit code like 'sp-perdizes'
    massagista_id: Optional[int] = None
    notes: Optional[str] = None
    promotion: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    client_name: str
    client_phone: str
    service: str
    appointment_date: datetime
    appointment_time: str
    status: str
    notes: Optional[str]
    unit_name: str
    massagista_name: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BookingStatusUpdate(BaseModel):
    status: BookingStatus

@router.post("/", response_model=BookingResponse)
async def create_booking(booking_data: BookingCreate, db: Session = Depends(get_db)):
    # Get unit by code
    unit = db.query(Unit).filter(Unit.code == booking_data.unit_id).first()
    if not unit:
        raise HTTPException(
            status_code=400,
            detail="Invalid unit"
        )
    
    # Validate massagista if provided
    massagista = None
    if booking_data.massagista_id:
        massagista = db.query(User).filter(
            and_(
                User.id == booking_data.massagista_id,
                User.user_type == "massagista",
                User.is_active == True
            )
        ).first()
        if not massagista:
            raise HTTPException(
                status_code=400,
                detail="Invalid massagista"
            )
    
    # Parse date and time
    try:
        appointment_date = datetime.strptime(booking_data.appointment_date, "%Y-%m-%d").date()
        appointment_time_obj = datetime.strptime(booking_data.appointment_time, "%H:%M").time()
        appointment_datetime = datetime.combine(appointment_date, appointment_time_obj)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date or time format"
        )
    
    # Check if slot is available
    existing_booking = db.query(Booking).filter(
        and_(
            Booking.unit_id == unit.id,
            Booking.appointment_date == appointment_datetime,
            Booking.appointment_time == booking_data.appointment_time,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).first()
    
    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail="Time slot is already booked"
        )
    
    # Create booking
    new_booking = Booking(
        client_name=booking_data.client_name,
        client_email=booking_data.client_email,
        client_phone=booking_data.client_phone,
        service=booking_data.service,
        appointment_date=appointment_datetime,
        appointment_time=booking_data.appointment_time,
        unit_id=unit.id,
        massagista_id=booking_data.massagista_id,
        notes=booking_data.notes,
        promotion=booking_data.promotion,
        status=BookingStatus.PENDING
    )
    
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    
    # Return formatted response
    return BookingResponse(
        id=new_booking.id,
        client_name=new_booking.client_name,
        client_phone=new_booking.client_phone,
        service=new_booking.service,
        appointment_date=new_booking.appointment_date,
        appointment_time=new_booking.appointment_time,
        status=new_booking.status.value,
        notes=new_booking.notes,
        unit_name=unit.name,
        massagista_name=massagista.name if massagista else None,
        created_at=new_booking.created_at
    )

@router.get("/", response_model=List[BookingResponse])
async def get_bookings(
    status: Optional[BookingStatus] = None,
    unit_code: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Booking).join(Unit).outerjoin(User, Booking.massagista_id == User.id)
    
    # Apply filters
    if status:
        query = query.filter(Booking.status == status)
    
    if unit_code:
        query = query.filter(Unit.code == unit_code)
    
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
    
    bookings = query.order_by(Booking.appointment_date.desc()).all()
    
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
            massagista_name=booking.massagista.name if booking.massagista else None,
            created_at=booking.created_at
        ))
    
    return response

@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).join(Unit).outerjoin(User, Booking.massagista_id == User.id).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )
    
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
        massagista_name=booking.massagista.name if booking.massagista else None,
        created_at=booking.created_at
    )

@router.put("/{booking_id}/status", response_model=BookingResponse)
async def update_booking_status(
    booking_id: int,
    status_update: BookingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )
    
    # Update status
    old_status = booking.status
    booking.status = status_update.status
    
    # Update timestamp fields
    if status_update.status == BookingStatus.CONFIRMED and old_status != BookingStatus.CONFIRMED:
        booking.confirmed_at = datetime.utcnow()
    elif status_update.status == BookingStatus.CANCELLED and old_status != BookingStatus.CANCELLED:
        booking.cancelled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(booking)
    
    # Return updated booking
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
        massagista_name=booking.massagista.name if booking.massagista else None,
        created_at=booking.created_at
    )

@router.get("/available-slots/{unit_code}")
async def get_available_slots(
    unit_code: str,
    date: str,  # YYYY-MM-DD format
    db: Session = Depends(get_db)
):
    # Get unit
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get existing bookings for the date
    existing_bookings = db.query(Booking).filter(
        and_(
            Booking.unit_id == unit.id,
            func.date(Booking.appointment_date) == target_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).all()
    
    booked_times = [booking.appointment_time for booking in existing_bookings]
    
    # Default available time slots
    all_slots = [
        "09:00", "10:00", "11:00", "14:00", "15:00", 
        "16:00", "17:00", "18:00", "19:00", "20:00"
    ]
    
    # Filter out booked slots
    available_slots = [slot for slot in all_slots if slot not in booked_times]
    
    return {
        "date": date,
        "unit": unit.name,
        "available_slots": available_slots,
        "booked_slots": booked_times
    }