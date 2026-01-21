"""
MedBook AI - Medical Appointment Booking Assistant
Main Streamlit Application Entry Point
"""
import os
import sys
import logging
import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.config import config
from app.chat_logic import get_chat_logic
from app.booking_flow import get_booking_flow
from app.rag_pipeline import get_rag_pipeline
from app.rate_limiter import get_rate_limiter
from app.admin_dashboard import check_admin_auth, admin_login, render_admin_dashboard
from utils.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def init_page_config():
    """Initialize Streamlit page configuration"""
    st.set_page_config(
        page_title=config.app_name,
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'About': f"# {config.app_name}\nAI-Powered Medical Appointment Booking Assistant"
        }
    )


def apply_custom_css():
    """Apply custom CSS styling"""
    st.markdown("""
    <style>
    /* Main theme colors */
    :root {
        --primary-color: #667eea;
        --secondary-color: #764ba2;
        --success-color: #28a745;
        --warning-color: #ffc107;
        --danger-color: #dc3545;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin-bottom: 20px;
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0;
    }
    
    /* Chat container */
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 10px;
    }
    
    /* Status badges */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .status-success {
        background: #d4edda;
        color: #155724;
    }
    
    .status-pending {
        background: #fff3cd;
        color: #856404;
    }
    
    .status-error {
        background: #f8d7da;
        color: #721c24;
    }
    
    /* Sidebar styling */
    .sidebar-section {
        background: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    
    /* PDF upload area */
    .upload-area {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background: #fafafa;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Improve chat message styling */
    .stChatMessage {
        padding: 10px 15px;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """Render the main header"""
    st.markdown(f"""
    <div class="main-header">
        <h1>🏥 {config.app_name}</h1>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">{config.clinic_name} - AI Booking Assistant</p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with navigation and controls"""
    with st.sidebar:
        st.markdown(f"## 🏥 {config.app_name}")
        
        # Navigation
        st.markdown("### Navigation")
        page = st.radio(
            "Select Page",
            options=["💬 Chat", "🔐 Admin"],
            key="nav_page",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # PDF Upload section (only on chat page)
        if "Chat" in page:
            st.markdown("### 📄 Knowledge Base")
            st.caption("Upload clinic documents for AI-powered Q&A")
            
            uploaded_files = st.file_uploader(
                "Upload PDFs",
                type=['pdf'],
                accept_multiple_files=True,
                key="pdf_uploader",
                help="Upload clinic policies, service guides, or other documents"
            )
            
            if uploaded_files:
                if st.button("📤 Process Documents", use_container_width=True):
                    with st.spinner("Processing documents..."):
                        rag = get_rag_pipeline()
                        success, count, errors = rag.process_pdfs(uploaded_files)
                        
                        if success:
                            st.success(f"✅ Processed {count} document(s)")
                        
                        for error in errors:
                            st.error(error)
            
            # Show document count
            rag = get_rag_pipeline()
            doc_count = rag.get_document_count()
            if doc_count > 0:
                st.info(f"📚 {doc_count} chunks indexed")
                if st.button("🗑️ Clear Documents", use_container_width=True):
                    rag.clear()
                    st.rerun()
            
            st.divider()
            
            # Booking status
            booking_flow = get_booking_flow()
            if booking_flow.is_active():
                st.markdown("### 📋 Current Booking")
                st.info(booking_flow.get_status_message())
                
                if st.button("❌ Cancel Booking", use_container_width=True):
                    booking_flow.reset()
                    st.rerun()
                
                st.divider()
            
            # Clear chat button
            if st.button("🗑️ Clear Chat", use_container_width=True):
                if 'messages' in st.session_state:
                    st.session_state.messages = []
                chat_logic = get_chat_logic()
                chat_logic.clear_memory()
                st.rerun()
        
        # Footer
        st.divider()
        
        return page


def render_chat_page():
    """Render the main chat interface"""
    render_header()
    
    # Initialize messages
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        # Add welcome message
        welcome_msg = f"""👋 Welcome to **{config.clinic_name}**!

I'm your AI booking assistant. I can help you:
• 📅 Schedule medical appointments
• ❓ Answer questions about our services
• 🔍 Look up your existing bookings

**To get started:**
- Say "I want to book an appointment" to schedule
- Upload clinic PDFs in the sidebar for Q&A
- Or just ask me anything!

How can I help you today?"""
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Rate limiting check
        rate_limiter = get_rate_limiter()
        allowed, error_msg = rate_limiter.check_message_rate()
        
        if not allowed:
            st.error(error_msg)
        else:
            # Record the message
            rate_limiter.record_message()
            
            # Add user message to display
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        chat_logic = get_chat_logic()
                        response = chat_logic.process_message(prompt)
                        st.markdown(response)
                        
                        # Add to messages
                        st.session_state.messages.append({"role": "assistant", "content": response})
                        
                    except Exception as e:
                        error_response = f"I apologize, but I encountered an error. Please try again. ({str(e)})"
                        st.error(error_response)
                        st.session_state.messages.append({"role": "assistant", "content": error_response})
                        logger.error(f"Chat error: {e}")


def render_admin_page():
    """Render the admin dashboard"""
    if not check_admin_auth():
        admin_login()
    else:
        render_admin_dashboard()


def check_configuration():
    """Check if all required configuration is present"""
    is_valid, errors = config.validate()
    
    if not is_valid:
        st.error("⚠️ Configuration Error")
        st.markdown("The following secrets are missing:")
        for error in errors:
            st.markdown(f"- {error}")
        st.markdown("""
        Please configure these in `.streamlit/secrets.toml` or Streamlit Cloud secrets.
        
        See `secrets.toml.template` for the required format.
        """)
        st.stop()


def main():
    """Main application entry point"""
    # Initialize page config first
    init_page_config()
    
    # Apply custom styling
    apply_custom_css()
    
    # Check configuration
    check_configuration()
    
    # Render sidebar and get selected page
    selected_page = render_sidebar()
    
    # Route to appropriate page
    if "Admin" in selected_page:
        render_admin_page()
    else:
        render_chat_page()


if __name__ == "__main__":
    main()
