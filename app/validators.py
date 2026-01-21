"""
Input validators for the booking system
Handles email, phone, date, and time validation with natural language support
"""
import re
from datetime import datetime, date, time, timedelta
from typing import Optional, Tuple
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
import html


# Email validation regex (RFC 5322 simplified)
EMAIL_REGEX = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Phone validation - at least 10 digits
PHONE_REGEX = re.compile(r'^\d{10,15}$')


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks
    """
    if not text:
        return ""
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Remove any potential SQL injection patterns
    dangerous_patterns = [
        r'--',  # SQL comment
        r';',   # SQL statement separator
        r'\'',  # Single quote
        r'"',   # Double quote (for JSON injection)
        r'<script',  # Script tags
        r'javascript:',  # JS protocol
        r'on\w+=',  # Event handlers
    ]
    
    for pattern in dangerous_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    return text.strip()


def validate_email(email: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate and clean email address
    Returns: (is_valid, cleaned_email or None, error_message)
    """
    if not email:
        return False, None, "Email address is required"
    
    email = email.strip().lower()
    
    if len(email) > 254:
        return False, None, "Email address is too long"
    
    if not EMAIL_REGEX.match(email):
        return False, None, "Please enter a valid email address (e.g., name@example.com)"
    
    return True, email, ""


def validate_phone(phone: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate and clean phone number
    Returns: (is_valid, cleaned_phone or None, error_message)
    """
    if not phone:
        return False, None, "Phone number is required"
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) < 10:
        return False, None, "Phone number must have at least 10 digits"
    
    if len(digits) > 15:
        return False, None, "Phone number is too long"
    
    return True, digits, ""


def parse_natural_date(date_str: str) -> Tuple[bool, Optional[str], str]:
    """
    Parse natural language date expressions
    Supports: "tomorrow", "next Monday", "Jan 25", "2026-01-25", etc.
    Returns: (is_valid, YYYY-MM-DD string or None, error_message)
    """
    if not date_str:
        return False, None, "Date is required"
    
    date_str = date_str.strip().lower()
    today = date.today()
    
    # Remove time components if present (handle "tomorrow afternoon" -> "tomorrow")
    time_words = ['morning', 'afternoon', 'evening', 'night', 'noon', 'midday']
    for tw in time_words:
        date_str = date_str.replace(tw, '').strip()
    
    # Also remove time patterns like "at 3pm"
    date_str = re.sub(r'\s+at\s+\d+.*$', '', date_str).strip()
    date_str = re.sub(r'\s+\d+\s*(am|pm).*$', '', date_str).strip()
    
    # Handle common natural language expressions
    if date_str in ['today', 'now', '']:
        result_date = today
    elif date_str == 'tomorrow':
        result_date = today + timedelta(days=1)
    elif date_str == 'day after tomorrow':
        result_date = today + timedelta(days=2)
    elif date_str.startswith('next '):
        day_name = date_str[5:].strip()
        day_map = {
            'monday': MO, 'tuesday': TU, 'wednesday': WE,
            'thursday': TH, 'friday': FR, 'saturday': SA, 'sunday': SU,
            'mon': MO, 'tue': TU, 'wed': WE, 'thu': TH, 'fri': FR, 'sat': SA, 'sun': SU
        }
        if day_name in day_map:
            result_date = today + relativedelta(weekday=day_map[day_name](+1))
        else:
            # Try standard parsing
            try:
                result_date = date_parser.parse(date_str, fuzzy=True).date()
            except Exception:
                return False, None, f"Could not understand '{date_str}'. Please use format YYYY-MM-DD or natural language like 'tomorrow', 'next Monday', 'Jan 25'"
    elif date_str.startswith('this '):
        day_name = date_str[5:].strip()
        day_map = {
            'monday': MO, 'tuesday': TU, 'wednesday': WE,
            'thursday': TH, 'friday': FR, 'saturday': SA, 'sunday': SU,
        }
        if day_name in day_map:
            result_date = today + relativedelta(weekday=day_map[day_name](0))
        else:
            try:
                result_date = date_parser.parse(date_str, fuzzy=True).date()
            except Exception:
                return False, None, f"Could not understand '{date_str}'. Please use a valid date format."
    else:
        # Try to parse with dateutil
        try:
            parsed = date_parser.parse(date_str, fuzzy=True, dayfirst=False)
            result_date = parsed.date()
            
            # If year is in the past and month/day could be in the future, assume next year
            if result_date < today and result_date.year == today.year:
                result_date = result_date.replace(year=today.year + 1)
            
        except Exception:
            return False, None, f"Could not understand '{date_str}'. Please use format YYYY-MM-DD or natural language like 'tomorrow', 'next Monday'"
    
    # Validate the date is not in the past
    if result_date < today:
        return False, None, "Appointment date cannot be in the past. Please choose a future date."
    
    # Validate not too far in the future (1 year max)
    max_date = today + timedelta(days=365)
    if result_date > max_date:
        return False, None, "Appointments can only be booked up to 1 year in advance."
    
    return True, result_date.strftime('%Y-%m-%d'), ""


def parse_natural_time(time_str: str) -> Tuple[bool, Optional[str], str]:
    """
    Parse natural language time expressions
    Supports: "3pm", "15:00", "3:30 PM", "morning", "afternoon", etc.
    Returns: (is_valid, HH:MM string or None, error_message)
    """
    if not time_str:
        return False, None, "Time is required"
    
    original_input = time_str
    time_str = time_str.strip().lower()
    
    # Remove extra whitespace
    time_str = ' '.join(time_str.split())
    
    # Handle natural language time periods
    time_periods = {
        'morning': '09:00',
        'late morning': '11:00',
        'noon': '12:00',
        'midday': '12:00',
        'afternoon': '14:00',
        'late afternoon': '16:00',
        'evening': '17:00',
        'early morning': '08:00',
    }
    
    if time_str in time_periods:
        return True, time_periods[time_str], ""
    
    # Normalize the time string for parsing
    # Remove all spaces first, then handle am/pm
    normalized = time_str.replace(' ', '').replace('.', ':')
    
    # Try to match patterns like "2pm", "3am", "10pm", "2:30pm"
    # Pattern: optional hour, optional :minutes, am/pm
    am_pm_match = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', normalized, re.IGNORECASE)
    if am_pm_match:
        hour = int(am_pm_match.group(1))
        minutes = am_pm_match.group(2) or '00'
        period = am_pm_match.group(3).lower()
        
        # Convert to 24-hour format
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        
        result_time = f"{hour:02d}:{minutes}"
        
        # Validate business hours (8 AM - 6 PM)
        if hour < 8:
            return False, None, "Appointments are available from 8:00 AM onwards."
        if hour >= 18:
            return False, None, "Appointments are available until 6:00 PM."
        
        return True, result_time, ""
    
    # Try 24-hour format: "14:30" or "14"
    time_24h_match = re.match(r'^(\d{1,2})(?::(\d{2}))?$', normalized)
    if time_24h_match:
        hour = int(time_24h_match.group(1))
        minutes = time_24h_match.group(2) or '00'
        
        if 0 <= hour <= 23:
            result_time = f"{hour:02d}:{minutes}"
            
            # Validate business hours
            if hour < 8:
                return False, None, "Appointments are available from 8:00 AM onwards."
            if hour >= 18:
                return False, None, "Appointments are available until 6:00 PM."
            
            return True, result_time, ""
    
    return False, None, f"Could not understand '{original_input}'. Please use format like '2pm', '14:30', or 'afternoon'"


def validate_name(name: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate and clean name
    Returns: (is_valid, cleaned_name or None, error_message)
    """
    if not name:
        return False, None, "Name is required"
    
    name = sanitize_input(name)
    
    if len(name) < 2:
        return False, None, "Name must be at least 2 characters"
    
    if len(name) > 100:
        return False, None, "Name is too long (max 100 characters)"
    
    # Check for only valid characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r'^[a-zA-Z\s\-\.\']+$', name):
        return False, None, "Name can only contain letters, spaces, hyphens, and apostrophes"
    
    # Title case the name
    name = ' '.join(word.capitalize() for word in name.split())
    
    return True, name, ""


def validate_booking_type(booking_type: str) -> Tuple[bool, Optional[str], str]:
    """
    Validate appointment type
    Returns: (is_valid, cleaned_type or None, error_message)
    """
    if not booking_type:
        return False, None, "Appointment type is required"
    
    booking_type = sanitize_input(booking_type)
    
    valid_types = [
        'general checkup', 'specialist consultation', 'follow-up visit',
        'vaccination', 'lab tests', 'dental care', 'eye examination',
        'physical therapy', 'mental health consultation', 'pediatric care', 'other'
    ]
    
    # Try to match or fuzzy match
    booking_lower = booking_type.lower()
    
    for vt in valid_types:
        if booking_lower == vt or booking_lower in vt or vt in booking_lower:
            # Return proper title case
            return True, vt.title(), ""
    
    # If no match, accept it anyway but clean it up
    return True, booking_type.title(), ""
