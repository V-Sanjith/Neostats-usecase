"""
Booking Flow Engine
Handles multi-turn slot filling and booking confirmation
"""
import os
import sys
import logging
from typing import Optional, Tuple, Dict, Any
from enum import Enum
import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.models import BookingSlots, CustomerCreate, BookingCreate, AppointmentType
from db.database import get_database, DatabaseError
from app.validators import (
    validate_name, validate_email, validate_phone,
    parse_natural_date, parse_natural_time, validate_booking_type
)
from utils.email_service import get_email_service

logger = logging.getLogger(__name__)


class BookingState(str, Enum):
    """States in the booking flow"""
    IDLE = "idle"
    COLLECTING = "collecting"
    CONFIRMING = "confirming"
    EDITING = "editing"
    COMPLETED = "completed"


class BookingFlow:
    """
    Manages the multi-turn booking conversation flow
    """
    
    # Field definitions with prompts
    FIELD_PROMPTS = {
        'name': "What is your full name?",
        'email': "What is your email address?",
        'phone': "What is your phone number?",
        'booking_type': f"What type of appointment would you like to schedule?\n\nAvailable types:\n" + 
                        "\n".join(f"• {t.value}" for t in AppointmentType),
        'date': "What date would you like to schedule your appointment?\n(You can say 'tomorrow', 'next Monday', or a specific date like 'Jan 25')",
        'time': "What time would you prefer?\n(You can say '3pm', 'morning', 'afternoon', or a specific time like '14:30')",
    }
    
    FIELD_ORDER = ['name', 'email', 'phone', 'booking_type', 'date', 'time']
    
    def __init__(self):
        self._initialize_session()
    
    def _initialize_session(self):
        """Initialize session state for booking flow"""
        if 'booking_state' not in st.session_state:
            st.session_state.booking_state = BookingState.IDLE
        if 'booking_slots' not in st.session_state:
            st.session_state.booking_slots = BookingSlots()
        if 'edit_field' not in st.session_state:
            st.session_state.edit_field = None
        if 'last_booking_id' not in st.session_state:
            st.session_state.last_booking_id = None
    
    @property
    def state(self) -> BookingState:
        return st.session_state.booking_state
    
    @state.setter
    def state(self, value: BookingState):
        st.session_state.booking_state = value
    
    @property
    def slots(self) -> BookingSlots:
        return st.session_state.booking_slots
    
    @slots.setter
    def slots(self, value: BookingSlots):
        st.session_state.booking_slots = value
    
    def start_booking(self) -> str:
        """Start a new booking flow"""
        self.state = BookingState.COLLECTING
        self.slots = BookingSlots()
        st.session_state.edit_field = None
        
        first_field = self.FIELD_ORDER[0]
        return f"I'd be happy to help you schedule an appointment! 🏥\n\n{self.FIELD_PROMPTS[first_field]}"
    
    def get_next_prompt(self) -> Optional[str]:
        """Get the prompt for the next missing field"""
        missing = self.slots.get_missing_fields()
        if not missing:
            return None
        
        next_field = None
        for field in self.FIELD_ORDER:
            if field in missing:
                next_field = field
                break
        
        if next_field:
            return self.FIELD_PROMPTS.get(next_field, f"Please provide your {next_field}:")
        return None
    
    def process_input(self, user_input: str) -> Tuple[str, bool]:
        """
        Process user input during booking flow
        
        Args:
            user_input: The user's message
            
        Returns:
            (response_message, is_complete)
        """
        user_input = user_input.strip()
        
        # Handle confirmation state
        if self.state == BookingState.CONFIRMING:
            return self._handle_confirmation(user_input)
        
        # Handle edit state
        if self.state == BookingState.EDITING:
            return self._handle_edit(user_input)
        
        # Handle collecting state - fill next missing field
        if self.state == BookingState.COLLECTING:
            return self._handle_collecting(user_input)
        
        return "Something went wrong. Let's start over.", False
    
    def _handle_collecting(self, user_input: str) -> Tuple[str, bool]:
        """Handle input during slot collection"""
        missing = self.slots.get_missing_fields()
        
        if not missing:
            # All fields collected, move to confirmation
            return self._show_confirmation(), False
        
        # Get the next field to fill
        current_field = None
        for field in self.FIELD_ORDER:
            if field in missing:
                current_field = field
                break
        
        # Validate and set the field
        result = self._validate_and_set_field(current_field, user_input)
        
        if result[0]:  # Valid
            # Check if all fields are now complete
            if self.slots.is_complete():
                return self._show_confirmation(), False
            else:
                # Get next prompt
                next_prompt = self.get_next_prompt()
                return f"✓ Got it!\n\n{next_prompt}", False
        else:
            # Invalid - return error and re-ask
            error_msg = result[1]
            return f"⚠️ {error_msg}\n\nPlease try again:", False
    
    def _validate_and_set_field(self, field: str, value: str) -> Tuple[bool, str]:
        """
        Validate and set a field value
        
        Returns:
            (success, error_message)
        """
        if field == 'name':
            is_valid, cleaned, error = validate_name(value)
            if is_valid:
                self.slots.name = cleaned
                return True, ""
            return False, error
        
        elif field == 'email':
            is_valid, cleaned, error = validate_email(value)
            if is_valid:
                self.slots.email = cleaned
                return True, ""
            return False, error
        
        elif field == 'phone':
            is_valid, cleaned, error = validate_phone(value)
            if is_valid:
                self.slots.phone = cleaned
                return True, ""
            return False, error
        
        elif field == 'booking_type':
            is_valid, cleaned, error = validate_booking_type(value)
            if is_valid:
                self.slots.booking_type = cleaned
                return True, ""
            return False, error
        
        elif field == 'date':
            is_valid, cleaned, error = parse_natural_date(value)
            if is_valid:
                self.slots.date = cleaned
                return True, ""
            return False, error
        
        elif field == 'time':
            is_valid, cleaned, error = parse_natural_time(value)
            if is_valid:
                self.slots.time = cleaned
                return True, ""
            return False, error
        
        return False, "Unknown field"
    
    def _show_confirmation(self) -> str:
        """Generate confirmation message"""
        self.state = BookingState.CONFIRMING
        
        summary = self.slots.to_summary()
        
        return f"""📋 **Please confirm your appointment details:**

{summary}

---

Is this information correct? 
- Reply **"yes"** or **"confirm"** to book
- Reply **"no"** or **"edit"** to make changes
- Reply **"cancel"** to start over"""
    
    def _handle_confirmation(self, user_input: str) -> Tuple[str, bool]:
        """Handle confirmation response"""
        response = user_input.lower().strip()
        
        # Positive confirmation
        if response in ['yes', 'y', 'confirm', 'confirmed', 'correct', 'ok', 'okay', 'yep', 'sure']:
            return self._save_booking()
        
        # Cancel
        if response in ['cancel', 'nevermind', 'never mind', 'abort', 'stop']:
            self.reset()
            return "Booking cancelled. Let me know if you'd like to schedule an appointment later!", False
        
        # Edit request
        if response in ['no', 'n', 'edit', 'change', 'modify', 'wrong']:
            return self._start_edit_mode(), False
        
        # Check if they're specifying a field to edit
        field_keywords = {
            'name': ['name'],
            'email': ['email', 'mail'],
            'phone': ['phone', 'number', 'mobile', 'cell'],
            'booking_type': ['type', 'appointment', 'service'],
            'date': ['date', 'day'],
            'time': ['time', 'hour']
        }
        
        for field, keywords in field_keywords.items():
            if any(kw in response for kw in keywords):
                st.session_state.edit_field = field
                self.state = BookingState.EDITING
                return f"What would you like to change the {field.replace('_', ' ')} to?", False
        
        return "I didn't understand that. Please reply 'yes' to confirm, 'edit' to make changes, or 'cancel' to start over.", False
    
    def _start_edit_mode(self) -> str:
        """Start edit mode"""
        self.state = BookingState.EDITING
        
        return """Which field would you like to change?

1. **Name**
2. **Email**
3. **Phone**
4. **Appointment Type**
5. **Date**
6. **Time**

Just type the field name or number:"""
    
    def _handle_edit(self, user_input: str) -> Tuple[str, bool]:
        """Handle edit input"""
        user_input = user_input.strip().lower()
        
        # If we already know which field to edit
        if st.session_state.edit_field:
            field = st.session_state.edit_field
            result = self._validate_and_set_field(field, user_input)
            
            if result[0]:
                st.session_state.edit_field = None
                return self._show_confirmation(), False
            else:
                return f"⚠️ {result[1]}\n\nPlease try again:", False
        
        # Determine which field to edit
        field_map = {
            '1': 'name', 'name': 'name',
            '2': 'email', 'email': 'email', 'mail': 'email',
            '3': 'phone', 'phone': 'phone', 'number': 'phone', 'mobile': 'phone',
            '4': 'booking_type', 'type': 'booking_type', 'appointment': 'booking_type', 'service': 'booking_type',
            '5': 'date', 'date': 'date', 'day': 'date',
            '6': 'time', 'time': 'time', 'hour': 'time',
        }
        
        for key, field in field_map.items():
            if key in user_input:
                st.session_state.edit_field = field
                current_value = getattr(self.slots, field, 'Not set')
                return f"Current {field.replace('_', ' ')}: **{current_value}**\n\nWhat would you like to change it to?", False
        
        return "I didn't understand which field you want to edit. Please type the field name (e.g., 'name', 'email', 'date') or number (1-6):", False
    
    def _save_booking(self) -> Tuple[str, bool]:
        """Save the booking to database and send confirmation"""
        try:
            db = get_database()
            
            # Create or get customer
            customer_data = CustomerCreate(
                name=self.slots.name,
                email=self.slots.email,
                phone=self.slots.phone
            )
            customer, is_new = db.get_or_create_customer(customer_data)
            
            # Create booking
            booking_data = BookingCreate(
                customer_id=customer.customer_id,
                booking_type=self.slots.booking_type,
                date=self.slots.date,
                time=self.slots.time,
                notes=self.slots.notes
            )
            booking = db.create_booking(booking_data)
            
            st.session_state.last_booking_id = booking.id
            logger.info(f"Booking created: ID={booking.id}")
            
            # Try to send email
            email_service = get_email_service()
            email_success, email_error = email_service.send_booking_confirmation(
                to_email=self.slots.email,
                customer_name=self.slots.name,
                booking_id=booking.id,
                booking_type=self.slots.booking_type,
                date=self.slots.date,
                time=self.slots.time,
                notes=self.slots.notes
            )
            
            # Build response
            success_msg = f"""🎉 **Appointment Booked Successfully!**

**Booking ID:** #{booking.id}

{self.slots.to_summary()}

---

"""
            
            if email_success:
                success_msg += f"✅ A confirmation email has been sent to **{self.slots.email}**"
            else:
                success_msg += f"⚠️ Your booking was saved, but we couldn't send the confirmation email. Please save your Booking ID (#{booking.id}) for reference."
                logger.warning(f"Email failed for booking {booking.id}: {email_error}")
            
            success_msg += "\n\nIs there anything else I can help you with?"
            
            # Reset state
            self.reset()
            
            return success_msg, True
            
        except DatabaseError as e:
            logger.error(f"Database error saving booking: {e}")
            self.state = BookingState.CONFIRMING
            return f"❌ Sorry, there was a problem saving your booking: {str(e)}\n\nWould you like to try again? (yes/no)", False
        
        except Exception as e:
            logger.error(f"Unexpected error saving booking: {e}")
            self.state = BookingState.CONFIRMING
            return "❌ An unexpected error occurred. Please try again or contact support.", False
    
    def reset(self):
        """Reset the booking flow"""
        self.state = BookingState.IDLE
        self.slots = BookingSlots()
        st.session_state.edit_field = None
    
    def is_active(self) -> bool:
        """Check if booking flow is currently active"""
        return self.state != BookingState.IDLE
    
    def get_status_message(self) -> str:
        """Get current status for UI display"""
        if self.state == BookingState.COLLECTING:
            missing = self.slots.get_missing_fields()
            filled = len(self.FIELD_ORDER) - len(missing)
            return f"📝 Collecting booking info ({filled}/{len(self.FIELD_ORDER)} fields)"
        elif self.state == BookingState.CONFIRMING:
            return "✅ Awaiting confirmation"
        elif self.state == BookingState.EDITING:
            return "✏️ Editing booking details"
        elif self.state == BookingState.COMPLETED:
            return "🎉 Booking complete"
        return ""


def get_booking_flow() -> BookingFlow:
    """Get booking flow instance"""
    if 'booking_flow_instance' not in st.session_state:
        st.session_state.booking_flow_instance = BookingFlow()
    return st.session_state.booking_flow_instance
