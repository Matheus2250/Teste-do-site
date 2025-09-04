from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import secrets
import hashlib

from app.models import User, Unit, Service, Booking, PasswordReset
from pydantic import EmailStr

# ============================================================================
# USER CRUD OPERATIONS
# ============================================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_user(db: Session, user_data: dict) -> User:
    """Create a new user in the database"""
    hashed_password = hash_password(user_data["password"])
    user = User(
        name=user_data["name"],
        email=user_data["email"],
        password=hashed_password,
        phone=user_data.get("phone"),
        user_type=user_data.get("user_type", "client"),
        unit_preference=user_data.get("unit_preference"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: EmailStr) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_all_users(db: Session) -> List[User]:
    """Get all active users"""
    return db.query(User).filter(User.is_active == True).all()

def update_user(db: Session, user_id: int, update_data: dict) -> Optional[User]:
    """Update user information"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    
    for key, value in update_data.items():
        if hasattr(user, key) and value is not None:
            setattr(user, key, value)
    
    db.commit()
    db.refresh(user)
    return user

def change_user_password(db: Session, user_id: int, new_password: str) -> bool:
    """Change user password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    
    user.password = hash_password(new_password)
    db.commit()
    return True

# ============================================================================
# UNIT CRUD OPERATIONS
# ============================================================================

def get_all_units(db: Session) -> List[Unit]:
    """Get all active units"""
    return db.query(Unit).filter(Unit.is_active == True).all()

def get_unit_by_id(db: Session, unit_id: int) -> Optional[Unit]:
    """Get unit by ID"""
    return db.query(Unit).filter(Unit.id == unit_id).first()

def get_unit_by_name(db: Session, name: str) -> Optional[Unit]:
    """Get unit by name"""
    return db.query(Unit).filter(Unit.name == name).first()

# ============================================================================
# SERVICE CRUD OPERATIONS
# ============================================================================

def get_all_services(db: Session) -> List[Service]:
    """Get all active services"""
    return db.query(Service).filter(Service.is_active == True).all()

def get_services_by_unit(db: Session, unit_id: int) -> List[Service]:
    """Get services for a specific unit"""
    return db.query(Service).filter(
        and_(Service.unit_id == unit_id, Service.is_active == True)
    ).all()

def get_service_by_id(db: Session, service_id: int) -> Optional[Service]:
    """Get service by ID"""
    return db.query(Service).filter(Service.id == service_id).first()

def get_service_by_name_and_unit(db: Session, name: str, unit_id: int) -> Optional[Service]:
    """Get service by name and unit"""
    return db.query(Service).filter(
        and_(Service.name == name, Service.unit_id == unit_id)
    ).first()

# ============================================================================
# BOOKING CRUD OPERATIONS
# ============================================================================

def create_booking(db: Session, booking_data: dict) -> Booking:
    """Create a new booking"""
    booking = Booking(**booking_data)
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

def get_bookings_by_user(db: Session, user_id: int) -> List[Booking]:
    """Get all bookings for a user"""
    return db.query(Booking).filter(Booking.user_id == user_id).all()

def get_bookings_by_unit(db: Session, unit_id: int) -> List[Booking]:
    """Get all bookings for a unit"""
    return db.query(Booking).filter(Booking.unit_id == unit_id).all()

def get_bookings_by_date_range(db: Session, start_date: datetime, end_date: datetime) -> List[Booking]:
    """Get bookings within a date range"""
    return db.query(Booking).filter(
        and_(Booking.booking_date >= start_date, Booking.booking_date <= end_date)
    ).all()

def get_booking_by_id(db: Session, booking_id: int) -> Optional[Booking]:
    """Get booking by ID"""
    return db.query(Booking).filter(Booking.id == booking_id).first()

def update_booking_status(db: Session, booking_id: int, status: str) -> Optional[Booking]:
    """Update booking status"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        return None
    
    booking.status = status
    db.commit()
    db.refresh(booking)
    return booking

def get_bookings_by_unit_and_date(db: Session, unit_id: int, booking_date: datetime) -> List[Booking]:
    """Get bookings for a unit on a specific date"""
    start_of_day = booking_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    return db.query(Booking).filter(
        and_(
            Booking.unit_id == unit_id,
            Booking.booking_date >= start_of_day,
            Booking.booking_date < end_of_day
        )
    ).all()

# ============================================================================
# PASSWORD RESET CRUD OPERATIONS
# ============================================================================

def create_password_reset_token(db: Session, user_id: int) -> PasswordReset:
    """Create a password reset token"""
    # Invalidate existing tokens for this user
    db.query(PasswordReset).filter(
        and_(PasswordReset.user_id == user_id, PasswordReset.is_used == False)
    ).update({"is_used": True})
    
    # Create new token
    token = secrets.token_hex(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    password_reset = PasswordReset(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    
    db.add(password_reset)
    db.commit()
    db.refresh(password_reset)
    return password_reset

def get_password_reset_token(db: Session, token: str) -> Optional[PasswordReset]:
    """Get valid password reset token"""
    return db.query(PasswordReset).filter(
        and_(
            PasswordReset.token == token,
            PasswordReset.is_used == False,
            PasswordReset.expires_at > datetime.utcnow()
        )
    ).first()

def use_password_reset_token(db: Session, token: str) -> bool:
    """Mark password reset token as used"""
    password_reset = get_password_reset_token(db, token)
    if not password_reset:
        return False
    
    password_reset.is_used = True
    db.commit()
    return True

def reset_user_password(db: Session, token: str, new_password: str) -> bool:
    """Reset user password using token"""
    password_reset = get_password_reset_token(db, token)
    if not password_reset:
        return False
    
    # Update user password
    user = password_reset.user
    user.password = hash_password(new_password)
    
    # Mark token as used
    password_reset.is_used = True
    
    db.commit()
    return True