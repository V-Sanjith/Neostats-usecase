"""
Chat Logic and Intent Detection
Handles conversation routing, memory management, and LLM interactions using Groq
"""
import os
import sys
import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum
import streamlit as st
from openai import OpenAI

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import config
from app.rag_pipeline import get_rag_pipeline
from app.booking_flow import get_booking_flow, BookingState
from db.database import get_database, DatabaseError

logger = logging.getLogger(__name__)

# Memory settings
MAX_MEMORY_MESSAGES = 25


class Intent(str, Enum):
    """User intent classification"""
    BOOKING = "booking"
    BOOKING_EDIT = "booking_edit"
    GENERAL = "general"
    GREETING = "greeting"
    LOOKUP = "lookup"
    HELP = "help"


class ChatLogic:
    """
    Main chat logic handler
    Manages conversation flow, intent detection, and response generation
    """
    
    def __init__(self):
        self._client = None
        self._model = "llama-3.3-70b-versatile"  # Groq's powerful Llama model
    
    @property
    def client(self) -> OpenAI:
        """Get or create Groq client (OpenAI-compatible)"""
        if self._client is None:
            api_key = config.groq_api_key
            if not api_key:
                raise ValueError("GROQ_API_KEY not configured")
            
            self._client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1"  # Groq endpoint
            )
        return self._client
    
    def get_memory(self) -> List[Dict]:
        """Get conversation memory from session state"""
        if 'chat_memory' not in st.session_state:
            st.session_state.chat_memory = []
        return st.session_state.chat_memory
    
    def add_to_memory(self, role: str, content: str):
        """Add a message to memory"""
        memory = self.get_memory()
        memory.append({"role": role, "content": content})
        
        # Trim to max size
        if len(memory) > MAX_MEMORY_MESSAGES:
            st.session_state.chat_memory = memory[-MAX_MEMORY_MESSAGES:]
    
    def clear_memory(self):
        """Clear conversation memory"""
        st.session_state.chat_memory = []
    
    def detect_intent(self, user_message: str) -> Intent:
        """
        Detect the user's intent from their message
        
        Args:
            user_message: The user's input
            
        Returns:
            Detected intent
        """
        message_lower = user_message.lower().strip()
        
        # Check if booking flow is active - prioritize booking intent
        booking_flow = get_booking_flow()
        if booking_flow.is_active():
            return Intent.BOOKING
        
        # Greeting patterns
        greetings = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy']
        if any(message_lower.startswith(g) for g in greetings) and len(message_lower.split()) <= 3:
            return Intent.GREETING
        
        # Help patterns
        help_patterns = ['help', 'what can you do', 'how to use', 'how does this work', 'options', 'menu']
        if any(p in message_lower for p in help_patterns):
            return Intent.HELP
        
        # Booking lookup patterns
        lookup_patterns = ['my appointments', 'my bookings', 'check my', 'find my', 'lookup', 'look up']
        if any(p in message_lower for p in lookup_patterns):
            return Intent.LOOKUP
        
        # Booking intent patterns (explicit)
        booking_patterns = [
            'book', 'schedule', 'appointment', 'reserve', 'make an appointment',
            'i want to', 'i need to', 'can i get', 'set up', 'arrange',
            'see a doctor', 'visit', 'consultation', 'checkup', 'check-up'
        ]
        if any(p in message_lower for p in booking_patterns):
            return Intent.BOOKING
        
        # Default to general (will use RAG or general chat)
        return Intent.GENERAL
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return f"""You are MedBook AI, a friendly and professional medical appointment booking assistant for {config.clinic_name}.

Your responsibilities:
1. Help patients schedule medical appointments
2. Answer questions about clinic services and uploaded documents
3. Be helpful, empathetic, and professional

Key information about the clinic:
- Name: {config.clinic_name}  
- Address: {config.clinic_address}
- Phone: {config.clinic_phone}
- Hours: Monday-Friday 8:00 AM - 6:00 PM

Available appointment types:
- General Checkup
- Specialist Consultation
- Follow-up Visit
- Vaccination
- Lab Tests
- Dental Care
- Eye Examination
- Physical Therapy
- Mental Health Consultation
- Pediatric Care

IMPORTANT - When document context is provided:
- The context comes from uploaded PDF documents - treat this as authoritative information
- Answer based on the provided context, summarizing and explaining the key points
- If asked about "the document" or "the PDF", refer to the context provided
- Remember the document name mentioned in the context for follow-up questions
- Be specific about what information comes from the documents

When responding:
- Be concise but thorough
- Use a warm, professional tone
- If you don't know something, say so honestly
- For booking requests, I will handle the booking flow separately"""
    
    def _call_llm(self, user_message: str, context: str = None) -> str:
        """
        Call the LLM for response generation using Groq
        
        Args:
            user_message: User's message
            context: Optional RAG context
            
        Returns:
            LLM response
        """
        try:
            messages = [{"role": "system", "content": self._get_system_prompt()}]
            
            # Add memory
            for msg in self.get_memory()[-10:]:  # Last 10 for LLM context
                messages.append(msg)
            
            # Add context if available (truncate to avoid token limits)
            if context:
                truncated_context = context[:3000] if len(context) > 3000 else context
                messages.append({
                    "role": "system",
                    "content": f"Use this context from clinic documents to help answer the user's question:\n\n{truncated_context}"
                })
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            response = self.client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=1024,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM call failed: {type(e).__name__}: {e}")
            # Try without context if that was the issue
            if context:
                try:
                    logger.info("Retrying LLM call without RAG context")
                    messages = [
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": user_message}
                    ]
                    response = self.client.chat.completions.create(
                        model=self._model,
                        messages=messages,
                        max_tokens=1024,
                        temperature=0.7
                    )
                    return response.choices[0].message.content + "\n\n*(Note: I couldn't access the uploaded documents for this answer)*"
                except Exception as e2:
                    logger.error(f"LLM retry also failed: {e2}")
            return f"I apologize, but I'm having trouble processing your request right now. Please try again in a moment."
    
    def process_message(self, user_message: str) -> str:
        """
        Process a user message and generate a response
        
        Args:
            user_message: The user's input
            
        Returns:
            Bot response
        """
        user_message = user_message.strip()
        
        if not user_message:
            return "I didn't catch that. Could you please repeat?"
        
        # Add to memory
        self.add_to_memory("user", user_message)
        
        # Detect intent
        intent = self.detect_intent(user_message)
        
        # Route based on intent
        if intent == Intent.GREETING:
            response = self._handle_greeting()
        
        elif intent == Intent.HELP:
            response = self._handle_help()
        
        elif intent == Intent.BOOKING:
            response = self._handle_booking(user_message)
        
        elif intent == Intent.LOOKUP:
            response = self._handle_lookup(user_message)
        
        else:  # GENERAL
            response = self._handle_general(user_message)
        
        # Add response to memory
        self.add_to_memory("assistant", response)
        
        return response
    
    def _handle_greeting(self) -> str:
        """Handle greeting messages"""
        clinic_name = config.clinic_name
        return f"""Hello! 👋 Welcome to {clinic_name}'s booking assistant.

I can help you with:
• 📅 **Schedule an appointment** - Just say "I want to book an appointment"
• ❓ **Answer questions** - Ask me anything about our services
• 🔍 **Look up your bookings** - Say "check my appointments"

How can I assist you today?"""
    
    def _handle_help(self) -> str:
        """Handle help requests"""
        return """Here's what I can help you with:

**📅 Book an Appointment**
Say something like:
- "I want to schedule an appointment"
- "Book a checkup for tomorrow"
- "I need to see a specialist"

**📄 Ask Questions**
If you've uploaded clinic documents (PDFs), I can answer questions about:
- Services and procedures
- Policies and guidelines
- Insurance information

**🔍 Look Up Bookings**
Say "Check my appointments" and provide your email to see your bookings.

**💬 General Chat**
Feel free to ask me anything about the clinic!

What would you like to do?"""
    
    def _handle_booking(self, user_message: str) -> str:
        """Handle booking-related messages"""
        booking_flow = get_booking_flow()
        
        if not booking_flow.is_active():
            # Start new booking
            return booking_flow.start_booking()
        else:
            # Continue booking flow
            response, is_complete = booking_flow.process_input(user_message)
            return response
    
    def _handle_lookup(self, user_message: str) -> str:
        """Handle booking lookup requests"""
        # Try to extract email from message
        import re
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, user_message)
        
        if match:
            email = match.group().lower()
            try:
                db = get_database()
                bookings = db.get_bookings_by_email(email)
                
                if not bookings:
                    return f"I couldn't find any appointments for **{email}**. Would you like to schedule a new appointment?"
                
                response = f"📋 **Your Appointments ({email}):**\n\n"
                for booking in bookings[:5]:  # Show last 5
                    status_icon = "✅" if booking.status == "CONFIRMED" else "⏳" if booking.status == "PENDING" else "❌"
                    response += f"{status_icon} **#{booking.id}** - {booking.booking_type}\n"
                    response += f"   📅 {booking.date} at {booking.time}\n\n"
                
                return response
                
            except DatabaseError as e:
                logger.error(f"Error looking up bookings: {e}")
                return "I'm having trouble accessing the booking system. Please try again later."
        else:
            return "To look up your appointments, please provide your email address.\n\nFor example: 'Check my appointments for john@example.com'"
    
    def _handle_general(self, user_message: str) -> str:
        """Handle general questions (with RAG if available)"""
        rag = get_rag_pipeline()
        
        # Always try RAG first if documents are available
        if rag.get_document_count() > 0:
            # Query RAG with context memory enabled for follow-ups
            context, sources = rag.query(user_message, use_context_memory=True)
            
            if context and sources and sources[0] not in ["No documents", "No relevant information found", "No sufficiently relevant information found"]:
                # Add document names to help LLM understand the context
                doc_names = rag.get_all_document_names()
                if doc_names:
                    context_intro = f"The following context is from uploaded document(s): {', '.join(doc_names)}\n\n"
                    context = context_intro + context
                
                # Generate response with context
                response = self._call_llm(user_message, context)
                
                # Add source attribution if it's actual document sources
                if sources and "Error" not in sources[0]:
                    response += f"\n\n📄 *Source: {', '.join(sources)}*"
                return response
        
        # No RAG context available, use general LLM response
        return self._call_llm(user_message)


def get_chat_logic() -> ChatLogic:
    """Get chat logic instance"""
    if 'chat_logic_instance' not in st.session_state:
        st.session_state.chat_logic_instance = ChatLogic()
    return st.session_state.chat_logic_instance
