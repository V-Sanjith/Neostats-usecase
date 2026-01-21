"""
Database models using Pydantic for validation
"""
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from enum import Enum
import re


class BookingStatus(str, Enum):
    """Booking status enumeration"""
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class AppointmentType(str, Enum):
    """Available appointment types"""
    GENERAL_CHECKUP = "General Checkup"
    SPECIALIST_CONSULTATION = "Specialist Consultation"
    FOLLOW_UP = "Follow-up Visit"
    VACCINATION = "Vaccination"
    LAB_TESTS = "Lab Tests"
    DENTAL = "Dental Care"
    EYE_EXAM = "Eye Examination"
    PHYSICAL_THERAPY = "Physical Therapy"
    MENTAL_HEALTH = "Mental Health Consultation"
    PEDIATRIC = "Pediatric Care"
    OTHER = "Other"


class CustomerCreate(BaseModel):
    """Model for creating a new customer"""
    name: str
    email: EmailStr
    phone: str
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Name must be less than 100 characters")
        # Basic sanitization - remove any HTML/script tags
        v = re.sub(r'<[^>]*>', '', v)
        return v
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: str) -> str:
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', v)
        if len(digits) < 10:
            raise ValueError("Phone number must have at least 10 digits")
        if len(digits) > 15:
            raise ValueError("Phone number is too long")
        return digits


class Customer(CustomerCreate):
    """Full customer model with ID"""
    customer_id: int
    created_at: Optional[datetime] = None


class BookingCreate(BaseModel):
    """Model for creating a new booking"""
    customer_id: int
    booking_type: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    notes: Optional[str] = None
    
    @field_validator('booking_type')
    @classmethod
    def validate_booking_type(cls, v: str) -> str:
        v = v.strip()
        valid_types = [t.value for t in AppointmentType]
        # Allow case-insensitive matching
        for valid_type in valid_types:
            if v.lower() == valid_type.lower():
                return valid_type
        # If not exact match, return as-is (for flexibility)
        return v
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
    
    @field_validator('time')
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
    
    @field_validator('notes')
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        if v:
            # Basic sanitization
            v = re.sub(r'<[^>]*>', '', v)
            return v[:500]  # Limit length
        return v


class Booking(BaseModel):
    """Full booking model with ID"""
    id: int
    customer_id: int
    booking_type: str
    date: str
    time: str
    status: BookingStatus = BookingStatus.CONFIRMED
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Joined fields
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class BookingSlots(BaseModel):
    """Tracks collected booking slots during conversation"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    notes: Optional[str] = None
    
    def get_missing_fields(self) -> list[str]:
        """Return list of fields that are still missing"""
        missing = []
        if not self.name:
            missing.append("name")
        if not self.email:
            missing.append("email")
        if not self.phone:
            missing.append("phone")
        if not self.booking_type:
            missing.append("booking_type")
        if not self.date:
            missing.append("date")
        if not self.time:
            missing.append("time")
        return missing
    
    def is_complete(self) -> bool:
        """Check if all required fields are collected"""
        return len(self.get_missing_fields()) == 0
    
    def to_summary(self) -> str:
        """Generate a human-readable summary"""
        lines = []
        if self.name:
            lines.append(f"**Name:** {self.name}")
        if self.email:
            lines.append(f"**Email:** {self.email}")
        if self.phone:
            lines.append(f"**Phone:** {self.phone}")
        if self.booking_type:
            lines.append(f"**Appointment Type:** {self.booking_type}")
        if self.date:
            lines.append(f"**Date:** {self.date}")
        if self.time:
            lines.append(f"**Time:** {self.time}")
        if self.notes:
            lines.append(f"**Notes:** {self.notes}")
        return "\n".join(lines)
