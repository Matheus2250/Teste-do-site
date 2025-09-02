from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from database.connection import Base

class BookingStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(255), nullable=False)
    client_email = Column(String(255), nullable=True)
    client_phone = Column(String(20), nullable=False)
    
    # Service details
    service = Column(String(100), nullable=False)  # shiatsu, relaxante, etc
    appointment_date = Column(DateTime, nullable=False)
    appointment_time = Column(String(10), nullable=False)  # HH:MM format
    duration_minutes = Column(Integer, default=60)
    
    # Location and staff
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    massagista_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Status and metadata
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)
    notes = Column(Text, nullable=True)
    promotion = Column(String(255), nullable=True)  # If booking came from promotion
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    unit = relationship("Unit", back_populates="bookings")
    massagista = relationship("User", back_populates="bookings_assigned")

class ServiceType(Base):
    __tablename__ = "service_types"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)  # shiatsu, relaxante, etc
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Integer, nullable=True)  # Price in cents
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Availability(Base):
    __tablename__ = "availability"

    id = Column(Integer, primary_key=True, index=True)
    massagista_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    start_time = Column(String(10), nullable=False)  # HH:MM
    end_time = Column(String(10), nullable=False)    # HH:MM
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    massagista = relationship("User")
    unit = relationship("Unit")