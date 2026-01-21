"""
Tool implementations for the AI Booking Assistant
These are exposed as callable functions for the agent/LLM
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.rag_pipeline import get_rag_pipeline
from db.database import get_database, DatabaseError
from db.models import CustomerCreate, BookingCreate
from utils.email_service import get_email_service

logger = logging.getLogger(__name__)


class RAGTool:
    """
    Tool for querying uploaded documents using RAG
    
    Input: user query string
    Output: generated answer with sources
    """
    
    name = "rag_query"
    description = "Query uploaded PDF documents to find relevant information"
    
    @staticmethod
    def execute(query: str) -> Dict[str, Any]:
        """
        Execute RAG query
        
        Args:
            query: User's question
            
        Returns:
            Dict with 'success', 'answer', 'sources', and 'error' fields
        """
        try:
            rag = get_rag_pipeline()
            
            if rag.get_document_count() == 0:
                return {
                    "success": False,
                    "answer": None,
                    "sources": [],
                    "error": "No documents have been uploaded. Please upload PDF files first."
                }
            
            context, sources = rag.query(query)
            
            if context is None:
                return {
                    "success": False,
                    "answer": None,
                    "sources": sources,  # Contains error message
                    "error": sources[0] if sources else "No relevant information found"
                }
            
            return {
                "success": True,
                "answer": context,
                "sources": sources,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"RAG tool error: {e}")
            return {
                "success": False,
                "answer": None,
                "sources": [],
                "error": f"Error querying documents: {str(e)}"
            }


class BookingTool:
    """
    Tool for persisting bookings to the database
    
    Input: structured booking payload
    Output: booking ID and status
    """
    
    name = "create_booking"
    description = "Save a new booking to the database"
    
    @staticmethod
    def execute(
        name: str,
        email: str,
        phone: str,
        booking_type: str,
        date: str,
        time: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new booking
        
        Args:
            name: Customer name
            email: Customer email
            phone: Customer phone
            booking_type: Type of appointment
            date: Appointment date (YYYY-MM-DD)
            time: Appointment time (HH:MM)
            notes: Optional notes
            
        Returns:
            Dict with 'success', 'booking_id', 'customer_id', and 'error' fields
        """
        try:
            db = get_database()
            
            # Create or get customer
            customer_data = CustomerCreate(
                name=name,
                email=email,
                phone=phone
            )
            customer, is_new = db.get_or_create_customer(customer_data)
            
            # Create booking
            booking_data = BookingCreate(
                customer_id=customer.customer_id,
                booking_type=booking_type,
                date=date,
                time=time,
                notes=notes
            )
            booking = db.create_booking(booking_data)
            
            logger.info(f"Booking created via tool: ID={booking.id}")
            
            return {
                "success": True,
                "booking_id": booking.id,
                "customer_id": customer.customer_id,
                "is_new_customer": is_new,
                "error": None
            }
            
        except DatabaseError as e:
            logger.error(f"Booking tool database error: {e}")
            return {
                "success": False,
                "booking_id": None,
                "customer_id": None,
                "error": f"Database error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Booking tool error: {e}")
            return {
                "success": False,
                "booking_id": None,
                "customer_id": None,
                "error": f"Failed to create booking: {str(e)}"
            }


class EmailTool:
    """
    Tool for sending emails
    
    Input: recipient, subject, body
    Output: success status
    """
    
    name = "send_email"
    description = "Send an email to a recipient"
    
    @staticmethod
    def execute(
        to_email: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body text
            
        Returns:
            Dict with 'success' and 'error' fields
        """
        try:
            email_service = get_email_service()
            success, error = email_service.send_custom_email(to_email, subject, body)
            
            if success:
                logger.info(f"Email sent successfully to {to_email}")
                return {
                    "success": True,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": error
                }
                
        except Exception as e:
            logger.error(f"Email tool error: {e}")
            return {
                "success": False,
                "error": f"Failed to send email: {str(e)}"
            }
    
    @staticmethod
    def send_booking_confirmation(
        to_email: str,
        customer_name: str,
        booking_id: int,
        booking_type: str,
        date: str,
        time: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send booking confirmation email
        
        Returns:
            Dict with 'success' and 'error' fields
        """
        try:
            email_service = get_email_service()
            success, error = email_service.send_booking_confirmation(
                to_email=to_email,
                customer_name=customer_name,
                booking_id=booking_id,
                booking_type=booking_type,
                date=date,
                time=time,
                notes=notes
            )
            
            return {
                "success": success,
                "error": error if not success else None
            }
            
        except Exception as e:
            logger.error(f"Email confirmation tool error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class BookingLookupTool:
    """
    Tool for looking up bookings by email
    
    Input: email address
    Output: list of bookings
    """
    
    name = "lookup_bookings"
    description = "Look up bookings by customer email"
    
    @staticmethod
    def execute(email: str) -> Dict[str, Any]:
        """
        Look up bookings for an email
        
        Args:
            email: Customer email address
            
        Returns:
            Dict with 'success', 'bookings', and 'error' fields
        """
        try:
            db = get_database()
            bookings = db.get_bookings_by_email(email)
            
            booking_list = []
            for b in bookings:
                booking_list.append({
                    "id": b.id,
                    "type": b.booking_type,
                    "date": b.date,
                    "time": b.time,
                    "status": b.status
                })
            
            return {
                "success": True,
                "bookings": booking_list,
                "count": len(booking_list),
                "error": None
            }
            
        except DatabaseError as e:
            logger.error(f"Booking lookup tool error: {e}")
            return {
                "success": False,
                "bookings": [],
                "count": 0,
                "error": str(e)
            }


# Tool registry for easy access
TOOLS = {
    "rag_query": RAGTool,
    "create_booking": BookingTool,
    "send_email": EmailTool,
    "lookup_bookings": BookingLookupTool
}


def get_tool(tool_name: str):
    """Get a tool by name"""
    return TOOLS.get(tool_name)


def list_tools() -> list:
    """List all available tools"""
    return [
        {
            "name": tool.name,
            "description": tool.description
        }
        for tool in TOOLS.values()
    ]
