from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    cpf = Column(String(14), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    user_type = Column(String(20), default="massagista")  # massagista, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    massagista_profile = relationship("MassagistaProfile", back_populates="user", uselist=False)
    bookings_assigned = relationship("Booking", back_populates="massagista")

class MassagistaProfile(Base):
    __tablename__ = "massagista_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    specialties = Column(Text, nullable=True)  # JSON string with specialties
    unit_preference = Column(String(50), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_available = Column(Boolean, default=True)
    working_hours = Column(Text, nullable=True)  # JSON string with schedule
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="massagista_profile")

class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)  # sp-perdizes, rj-centro, etc
    name = Column(String(255), nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(2), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    working_hours = Column(Text, nullable=True)  # JSON string
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    bookings = relationship("Booking", back_populates="unit")