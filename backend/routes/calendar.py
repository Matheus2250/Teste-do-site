from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time, timedelta
import calendar as cal
from collections import defaultdict

from database.connection import get_db
from models.bookings import Booking, BookingStatus
from models.users import User, Unit
from utils.auth import get_current_user

router = APIRouter()

# Pydantic models
class DayAvailability(BaseModel):
    date: str
    day_of_week: str
    available_slots: List[str]
    booked_slots: List[str]
    total_slots: int
    available_count: int
    is_weekend: bool
    is_holiday: bool = False

class WeekAvailability(BaseModel):
    week_start: str
    week_end: str
    days: List[DayAvailability]
    week_stats: Dict[str, Any]

class MonthAvailability(BaseModel):
    year: int
    month: int
    month_name: str
    weeks: List[WeekAvailability]
    month_stats: Dict[str, Any]

class CalendarStatsRequest(BaseModel):
    unit_code: Optional[str] = None
    massagista_id: Optional[int] = None
    date_from: str
    date_to: str

class TimeSlotInfo(BaseModel):
    time: str
    available: bool
    booked_by: Optional[str] = None
    service: Optional[str] = None
    massagista_name: Optional[str] = None

class AdvancedDayView(BaseModel):
    date: str
    unit_name: str
    slots: List[TimeSlotInfo]
    total_bookings: int
    revenue_estimate: float

# Default time slots configuration
DEFAULT_SLOTS = [
    "09:00", "10:00", "11:00", "12:00",
    "14:00", "15:00", "16:00", "17:00", 
    "18:00", "19:00", "20:00"
]

WEEKEND_SLOTS = [
    "09:00", "10:00", "11:00", "14:00", 
    "15:00", "16:00", "17:00", "18:00"
]

def get_default_slots(target_date: date) -> List[str]:
    """Get default time slots based on day of week"""
    if target_date.weekday() >= 5:  # Saturday=5, Sunday=6
        return WEEKEND_SLOTS
    return DEFAULT_SLOTS

def is_holiday(target_date: date) -> bool:
    """Check if date is a Brazilian holiday"""
    # Simplified holiday check - extend as needed
    holidays_2024 = [
        date(2024, 1, 1),   # New Year
        date(2024, 4, 21),  # Tiradentes
        date(2024, 9, 7),   # Independence Day
        date(2024, 10, 12), # Our Lady of Aparecida
        date(2024, 11, 15), # Proclamation of Republic
        date(2024, 12, 25), # Christmas
    ]
    return target_date in holidays_2024

@router.get("/availability/day/{unit_code}/{date}")
async def get_day_availability(
    unit_code: str, 
    date: str,
    massagista_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """Get detailed availability for a specific day"""
    # Validate unit
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    # Parse date
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get existing bookings
    query = db.query(Booking).filter(
        and_(
            Booking.unit_id == unit.id,
            func.date(Booking.appointment_date) == target_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    )
    
    if massagista_id:
        query = query.filter(Booking.massagista_id == massagista_id)
    
    bookings = query.all()
    
    # Get booked times
    booked_times = [booking.appointment_time for booking in bookings]
    
    # Get available slots based on day
    all_slots = get_default_slots(target_date)
    available_slots = [slot for slot in all_slots if slot not in booked_times]
    
    # Create time slot details
    slots = []
    for time_slot in all_slots:
        booking = next((b for b in bookings if b.appointment_time == time_slot), None)
        slot_info = TimeSlotInfo(
            time=time_slot,
            available=booking is None,
            booked_by=booking.client_name if booking else None,
            service=booking.service if booking else None,
            massagista_name=booking.massagista.name if booking and booking.massagista else None
        )
        slots.append(slot_info)
    
    # Calculate revenue estimate (simplified)
    revenue_estimate = len([b for b in bookings if b.service]) * 100.0  # Average price
    
    return AdvancedDayView(
        date=date,
        unit_name=unit.name,
        slots=slots,
        total_bookings=len(bookings),
        revenue_estimate=revenue_estimate
    )

@router.get("/availability/week/{unit_code}")
async def get_week_availability(
    unit_code: str,
    week_start: str = Query(..., description="Start of week in YYYY-MM-DD format"),
    db: Session = Depends(get_db)
):
    """Get availability for a full week"""
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    try:
        start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
        end_date = start_date + timedelta(days=6)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get all bookings for the week
    bookings = db.query(Booking).filter(
        and_(
            Booking.unit_id == unit.id,
            func.date(Booking.appointment_date) >= start_date,
            func.date(Booking.appointment_date) <= end_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).all()
    
    # Group bookings by date
    bookings_by_date = defaultdict(list)
    for booking in bookings:
        booking_date = booking.appointment_date.date()
        bookings_by_date[booking_date].append(booking)
    
    # Generate day availability for each day
    days = []
    total_available = 0
    total_booked = 0
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_bookings = bookings_by_date[current_date]
        booked_times = [b.appointment_time for b in day_bookings]
        
        all_slots = get_default_slots(current_date)
        available_slots = [slot for slot in all_slots if slot not in booked_times]
        
        day_availability = DayAvailability(
            date=current_date.strftime("%Y-%m-%d"),
            day_of_week=current_date.strftime("%A"),
            available_slots=available_slots,
            booked_slots=booked_times,
            total_slots=len(all_slots),
            available_count=len(available_slots),
            is_weekend=current_date.weekday() >= 5,
            is_holiday=is_holiday(current_date)
        )
        
        days.append(day_availability)
        total_available += len(available_slots)
        total_booked += len(booked_times)
    
    week_stats = {
        "total_available_slots": total_available,
        "total_booked_slots": total_booked,
        "occupancy_rate": (total_booked / (total_available + total_booked) * 100) if (total_available + total_booked) > 0 else 0,
        "busiest_day": max(days, key=lambda d: len(d.booked_slots)).day_of_week if days else None
    }
    
    return WeekAvailability(
        week_start=week_start,
        week_end=end_date.strftime("%Y-%m-%d"),
        days=days,
        week_stats=week_stats
    )

@router.get("/availability/month/{unit_code}/{year}/{month}")
async def get_month_availability(
    unit_code: str,
    year: int,
    month: int,
    db: Session = Depends(get_db)
):
    """Get availability for a full month"""
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Invalid month")
    
    # Get first and last day of month
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Get all bookings for the month
    bookings = db.query(Booking).filter(
        and_(
            Booking.unit_id == unit.id,
            func.date(Booking.appointment_date) >= first_day,
            func.date(Booking.appointment_date) <= last_day,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    ).all()
    
    # Group bookings by date
    bookings_by_date = defaultdict(list)
    for booking in bookings:
        booking_date = booking.appointment_date.date()
        bookings_by_date[booking_date].append(booking)
    
    # Generate weeks
    weeks = []
    current_date = first_day
    
    while current_date <= last_day:
        # Find start of week (Monday)
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        # Generate week if it intersects with the month
        if week_start <= last_day and week_end >= first_day:
            week_availability = await get_week_availability(
                unit_code=unit_code,
                week_start=week_start.strftime("%Y-%m-%d"),
                db=db
            )
            weeks.append(week_availability)
        
        # Move to next week
        current_date = week_end + timedelta(days=1)
    
    # Calculate month stats
    total_bookings = len(bookings)
    total_revenue = sum(100.0 for b in bookings)  # Simplified revenue calculation
    
    month_stats = {
        "total_bookings": total_bookings,
        "total_revenue_estimate": total_revenue,
        "average_daily_bookings": total_bookings / (last_day - first_day + timedelta(days=1)).days,
        "busiest_week": max(weeks, key=lambda w: w.week_stats["total_booked_slots"]).week_start if weeks else None
    }
    
    return MonthAvailability(
        year=year,
        month=month,
        month_name=cal.month_name[month],
        weeks=weeks,
        month_stats=month_stats
    )

@router.get("/stats/availability")
async def get_availability_stats(
    unit_code: Optional[str] = Query(None),
    massagista_id: Optional[int] = Query(None),
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: Session = Depends(get_db)
):
    """Get comprehensive availability statistics"""
    try:
        from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
        to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Build query
    query = db.query(Booking).filter(
        and_(
            func.date(Booking.appointment_date) >= from_date,
            func.date(Booking.appointment_date) <= to_date,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
        )
    )
    
    if unit_code:
        unit = db.query(Unit).filter(Unit.code == unit_code).first()
        if not unit:
            raise HTTPException(status_code=400, detail="Invalid unit")
        query = query.filter(Booking.unit_id == unit.id)
    
    if massagista_id:
        query = query.filter(Booking.massagista_id == massagista_id)
    
    bookings = query.all()
    
    # Calculate stats
    days_count = (to_date - from_date).days + 1
    total_possible_slots = days_count * len(DEFAULT_SLOTS)
    total_bookings = len(bookings)
    
    # Group by date for daily analysis
    daily_bookings = defaultdict(int)
    for booking in bookings:
        daily_bookings[booking.appointment_date.date()] += 1
    
    # Find peak patterns
    hourly_distribution = defaultdict(int)
    service_distribution = defaultdict(int)
    
    for booking in bookings:
        hourly_distribution[booking.appointment_time] += 1
        service_distribution[booking.service] += 1
    
    peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else None
    popular_service = max(service_distribution.items(), key=lambda x: x[1])[0] if service_distribution else None
    
    return {
        "period": {
            "from": date_from,
            "to": date_to,
            "days": days_count
        },
        "bookings": {
            "total": total_bookings,
            "average_per_day": total_bookings / days_count,
            "occupancy_rate": (total_bookings / total_possible_slots * 100) if total_possible_slots > 0 else 0
        },
        "patterns": {
            "peak_hour": peak_hour,
            "popular_service": popular_service,
            "hourly_distribution": dict(hourly_distribution),
            "service_distribution": dict(service_distribution)
        },
        "revenue": {
            "estimated_total": total_bookings * 100.0,  # Simplified
            "average_per_booking": 100.0,
            "average_per_day": (total_bookings * 100.0) / days_count
        }
    }

@router.get("/next-available/{unit_code}")
async def find_next_available_slot(
    unit_code: str,
    from_date: Optional[str] = Query(None),
    service_duration: Optional[int] = Query(60, description="Service duration in minutes"),
    db: Session = Depends(get_db)
):
    """Find the next available time slot"""
    unit = db.query(Unit).filter(Unit.code == unit_code).first()
    if not unit:
        raise HTTPException(status_code=400, detail="Invalid unit")
    
    # Start from today or specified date
    if from_date:
        try:
            start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        start_date = datetime.now().date()
    
    # Look for available slots in the next 30 days
    for i in range(30):
        check_date = start_date + timedelta(days=i)
        
        # Get bookings for this date
        existing_bookings = db.query(Booking).filter(
            and_(
                Booking.unit_id == unit.id,
                func.date(Booking.appointment_date) == check_date,
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED])
            )
        ).all()
        
        booked_times = [b.appointment_time for b in existing_bookings]
        available_slots = get_default_slots(check_date)
        
        # Find first available slot
        for slot in available_slots:
            if slot not in booked_times:
                return {
                    "next_available": {
                        "date": check_date.strftime("%Y-%m-%d"),
                        "time": slot,
                        "day_of_week": check_date.strftime("%A"),
                        "days_from_now": i
                    },
                    "alternatives": [
                        {
                            "time": alt_slot,
                            "available": alt_slot not in booked_times
                        }
                        for alt_slot in available_slots[:5]  # Show first 5 slots
                    ]
                }
    
    return {"message": "No available slots found in the next 30 days"}