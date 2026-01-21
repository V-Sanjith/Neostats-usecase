"""
Rate limiter for preventing abuse
Session-based limiting for chat requests and booking attempts
"""
import time
from typing import Tuple
import streamlit as st
from collections import deque


class RateLimiter:
    """Session-based rate limiter"""
    
    def __init__(
        self,
        max_messages_per_minute: int = 30,
        max_bookings_per_hour: int = 5,
        cooldown_seconds: int = 2
    ):
        self.max_messages_per_minute = max_messages_per_minute
        self.max_bookings_per_hour = max_bookings_per_hour
        self.cooldown_seconds = cooldown_seconds
    
    def _get_message_timestamps(self) -> deque:
        """Get or initialize message timestamps deque"""
        if 'rate_limit_messages' not in st.session_state:
            st.session_state.rate_limit_messages = deque(maxlen=100)
        return st.session_state.rate_limit_messages
    
    def _get_booking_timestamps(self) -> deque:
        """Get or initialize booking timestamps deque"""
        if 'rate_limit_bookings' not in st.session_state:
            st.session_state.rate_limit_bookings = deque(maxlen=20)
        return st.session_state.rate_limit_bookings
    
    def _get_last_message_time(self) -> float:
        """Get last message timestamp"""
        return st.session_state.get('last_message_time', 0)
    
    def _set_last_message_time(self, timestamp: float):
        """Set last message timestamp"""
        st.session_state.last_message_time = timestamp
    
    def check_message_rate(self) -> Tuple[bool, str]:
        """
        Check if a new message is allowed
        
        Returns:
            (is_allowed, error_message)
        """
        current_time = time.time()
        
        # Check cooldown (prevent rapid submissions)
        last_time = self._get_last_message_time()
        if current_time - last_time < self.cooldown_seconds:
            remaining = self.cooldown_seconds - (current_time - last_time)
            return False, f"Please wait {remaining:.1f} seconds before sending another message."
        
        # Check rate limit
        timestamps = self._get_message_timestamps()
        
        # Remove old timestamps (older than 1 minute)
        minute_ago = current_time - 60
        while timestamps and timestamps[0] < minute_ago:
            timestamps.popleft()
        
        if len(timestamps) >= self.max_messages_per_minute:
            return False, f"Rate limit exceeded. Please wait a moment before sending more messages. (Max {self.max_messages_per_minute} messages per minute)"
        
        return True, ""
    
    def record_message(self):
        """Record a new message timestamp"""
        current_time = time.time()
        self._get_message_timestamps().append(current_time)
        self._set_last_message_time(current_time)
    
    def check_booking_rate(self) -> Tuple[bool, str]:
        """
        Check if a new booking attempt is allowed
        
        Returns:
            (is_allowed, error_message)
        """
        current_time = time.time()
        timestamps = self._get_booking_timestamps()
        
        # Remove old timestamps (older than 1 hour)
        hour_ago = current_time - 3600
        while timestamps and timestamps[0] < hour_ago:
            timestamps.popleft()
        
        if len(timestamps) >= self.max_bookings_per_hour:
            return False, f"You've made too many booking attempts. Please wait before trying again. (Max {self.max_bookings_per_hour} bookings per hour)"
        
        return True, ""
    
    def record_booking(self):
        """Record a new booking attempt timestamp"""
        self._get_booking_timestamps().append(time.time())
    
    def get_remaining_capacity(self) -> dict:
        """Get remaining rate limit capacity"""
        current_time = time.time()
        
        # Messages
        msg_timestamps = self._get_message_timestamps()
        minute_ago = current_time - 60
        recent_messages = sum(1 for t in msg_timestamps if t >= minute_ago)
        
        # Bookings
        booking_timestamps = self._get_booking_timestamps()
        hour_ago = current_time - 3600
        recent_bookings = sum(1 for t in booking_timestamps if t >= hour_ago)
        
        return {
            'messages_remaining': self.max_messages_per_minute - recent_messages,
            'bookings_remaining': self.max_bookings_per_hour - recent_bookings
        }


# Singleton
_rate_limiter: RateLimiter = None


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
