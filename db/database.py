"""
Database operations using Supabase
Handles all CRUD operations for customers and bookings
"""
import logging
from typing import Optional, Tuple
from supabase import create_client, Client
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import config
from db.models import CustomerCreate, Customer, BookingCreate, Booking, BookingStatus

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass


class Database:
    """Supabase database client with CRUD operations"""
    
    _instance: Optional['Database'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Supabase client"""
        try:
            url = config.supabase_url
            key = config.supabase_service_role_key or config.supabase_anon_key
            
            if not url or not key:
                raise DatabaseError("Supabase credentials not configured")
            
            self._client = create_client(url, key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
    
    @property
    def client(self) -> Client:
        """Get the Supabase client"""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    # ==================== Customer Operations ====================
    
    def get_customer_by_email(self, email: str) -> Optional[Customer]:
        """Get a customer by email address"""
        try:
            response = self.client.table('customers').select('*').eq('email', email.lower()).execute()
            if response.data and len(response.data) > 0:
                return Customer(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching customer by email: {e}")
            raise DatabaseError(f"Failed to fetch customer: {e}")
    
    def create_customer(self, customer: CustomerCreate) -> Customer:
        """Create a new customer"""
        try:
            data = {
                'name': customer.name,
                'email': customer.email.lower(),
                'phone': customer.phone
            }
            response = self.client.table('customers').insert(data).execute()
            if response.data and len(response.data) > 0:
                logger.info(f"Created customer: {customer.email}")
                return Customer(**response.data[0])
            raise DatabaseError("Failed to create customer - no data returned")
        except Exception as e:
            if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                # Customer already exists, fetch and return
                existing = self.get_customer_by_email(customer.email)
                if existing:
                    return existing
            logger.error(f"Error creating customer: {e}")
            raise DatabaseError(f"Failed to create customer: {e}")
    
    def get_or_create_customer(self, customer: CustomerCreate) -> Tuple[Customer, bool]:
        """Get existing customer or create new one. Returns (customer, is_new)"""
        existing = self.get_customer_by_email(customer.email)
        if existing:
            # Update name and phone if they've changed
            try:
                self.client.table('customers').update({
                    'name': customer.name,
                    'phone': customer.phone
                }).eq('customer_id', existing.customer_id).execute()
            except Exception as e:
                logger.warning(f"Failed to update customer: {e}")
            return existing, False
        
        new_customer = self.create_customer(customer)
        return new_customer, True
    
    # ==================== Booking Operations ====================
    
    def create_booking(self, booking: BookingCreate) -> Booking:
        """Create a new booking"""
        try:
            data = {
                'customer_id': booking.customer_id,
                'booking_type': booking.booking_type,
                'date': booking.date,
                'time': booking.time,
                'status': BookingStatus.CONFIRMED.value,
                'notes': booking.notes
            }
            response = self.client.table('bookings').insert(data).execute()
            if response.data and len(response.data) > 0:
                logger.info(f"Created booking ID: {response.data[0]['id']}")
                return Booking(**response.data[0])
            raise DatabaseError("Failed to create booking - no data returned")
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            raise DatabaseError(f"Failed to create booking: {e}")
    
    def get_booking_by_id(self, booking_id: int) -> Optional[Booking]:
        """Get a booking by ID with customer details"""
        try:
            response = self.client.table('bookings').select(
                '*, customers(name, email, phone)'
            ).eq('id', booking_id).execute()
            
            if response.data and len(response.data) > 0:
                data = response.data[0]
                customer_data = data.pop('customers', {}) or {}
                return Booking(
                    **data,
                    customer_name=customer_data.get('name'),
                    customer_email=customer_data.get('email'),
                    customer_phone=customer_data.get('phone')
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching booking: {e}")
            raise DatabaseError(f"Failed to fetch booking: {e}")
    
    def get_bookings_by_email(self, email: str) -> list[Booking]:
        """Get all bookings for a customer by email"""
        try:
            customer = self.get_customer_by_email(email)
            if not customer:
                return []
            
            response = self.client.table('bookings').select('*').eq(
                'customer_id', customer.customer_id
            ).order('date', desc=True).execute()
            
            bookings = []
            for data in response.data or []:
                bookings.append(Booking(
                    **data,
                    customer_name=customer.name,
                    customer_email=customer.email,
                    customer_phone=customer.phone
                ))
            return bookings
        except Exception as e:
            logger.error(f"Error fetching bookings by email: {e}")
            raise DatabaseError(f"Failed to fetch bookings: {e}")
    
    def get_all_bookings(self, limit: int = 100, offset: int = 0) -> list[Booking]:
        """Get all bookings with customer details (for admin)"""
        try:
            response = self.client.table('bookings').select(
                '*, customers(name, email, phone)'
            ).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
            
            bookings = []
            for data in response.data or []:
                customer_data = data.pop('customers', {}) or {}
                bookings.append(Booking(
                    **data,
                    customer_name=customer_data.get('name'),
                    customer_email=customer_data.get('email'),
                    customer_phone=customer_data.get('phone')
                ))
            return bookings
        except Exception as e:
            logger.error(f"Error fetching all bookings: {e}")
            raise DatabaseError(f"Failed to fetch bookings: {e}")
    
    def search_bookings(
        self, 
        search_term: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[BookingStatus] = None
    ) -> list[Booking]:
        """Search bookings with filters (for admin)"""
        try:
            # Start with base query
            query = self.client.table('bookings').select(
                '*, customers(name, email, phone)'
            )
            
            # Apply filters
            if date_from:
                query = query.gte('date', date_from)
            if date_to:
                query = query.lte('date', date_to)
            if status:
                query = query.eq('status', status.value)
            
            response = query.order('created_at', desc=True).execute()
            
            bookings = []
            for data in response.data or []:
                customer_data = data.pop('customers', {}) or {}
                
                # Apply text search filter (client-side for simplicity)
                if search_term:
                    search_lower = search_term.lower()
                    name = (customer_data.get('name') or '').lower()
                    email = (customer_data.get('email') or '').lower()
                    if search_lower not in name and search_lower not in email:
                        continue
                
                bookings.append(Booking(
                    **data,
                    customer_name=customer_data.get('name'),
                    customer_email=customer_data.get('email'),
                    customer_phone=customer_data.get('phone')
                ))
            return bookings
        except Exception as e:
            logger.error(f"Error searching bookings: {e}")
            raise DatabaseError(f"Failed to search bookings: {e}")
    
    def update_booking_status(self, booking_id: int, status: BookingStatus) -> bool:
        """Update booking status"""
        try:
            response = self.client.table('bookings').update({
                'status': status.value
            }).eq('id', booking_id).execute()
            return len(response.data or []) > 0
        except Exception as e:
            logger.error(f"Error updating booking status: {e}")
            return False
    
    def get_booking_count(self) -> int:
        """Get total number of bookings"""
        try:
            response = self.client.table('bookings').select('id', count='exact').execute()
            return response.count or 0
        except Exception as e:
            logger.error(f"Error getting booking count: {e}")
            return 0


# SQL to create tables in Supabase (run this in Supabase SQL editor)
CREATE_TABLES_SQL = """
-- Create customers table
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create bookings table
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    booking_type TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    status TEXT DEFAULT 'CONFIRMED',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_bookings_customer_id ON bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

-- Enable Row Level Security (optional but recommended)
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookings ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (adjust based on your security needs)
CREATE POLICY "Allow all operations on customers" ON customers FOR ALL USING (true);
CREATE POLICY "Allow all operations on bookings" ON bookings FOR ALL USING (true);
"""


def get_database() -> Database:
    """Get the database singleton instance"""
    return Database()
