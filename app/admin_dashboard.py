"""
Admin Dashboard
Protected interface for viewing and managing bookings
"""
import os
import sys
import logging
from datetime import datetime, date, timedelta
import streamlit as st
import csv
from io import StringIO

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.config import config
from db.database import get_database, DatabaseError
from db.models import BookingStatus

logger = logging.getLogger(__name__)


def check_admin_auth() -> bool:
    """Check if admin is authenticated"""
    return st.session_state.get('admin_authenticated', False)


def admin_login():
    """Render admin login form"""
    st.markdown("""
    <style>
    .admin-login {
        max-width: 400px;
        margin: 50px auto;
        padding: 30px;
        background: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🔐 Admin Login")
    st.markdown("Please enter the admin password to access the dashboard.")
    
    with st.form("admin_login_form"):
        password = st.text_input("Password", type="password", key="admin_password_input")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if password == config.admin_password:
                st.session_state.admin_authenticated = True
                st.session_state.login_attempts = 0
                logger.info("Admin login successful")
                st.rerun()
            else:
                # Track failed attempts
                attempts = st.session_state.get('login_attempts', 0) + 1
                st.session_state.login_attempts = attempts
                
                if attempts >= 5:
                    st.error("⚠️ Too many failed attempts. Please wait before trying again.")
                    logger.warning(f"Admin login: {attempts} failed attempts")
                else:
                    st.error(f"❌ Incorrect password. ({5 - attempts} attempts remaining)")


def admin_logout():
    """Handle admin logout"""
    st.session_state.admin_authenticated = False
    st.rerun()


def export_bookings_csv(bookings) -> str:
    """Export bookings to CSV string"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Booking ID', 'Customer Name', 'Email', 'Phone',
        'Appointment Type', 'Date', 'Time', 'Status', 'Created At'
    ])
    
    # Data
    for booking in bookings:
        writer.writerow([
            booking.id,
            booking.customer_name or 'N/A',
            booking.customer_email or 'N/A',
            booking.customer_phone or 'N/A',
            booking.booking_type,
            booking.date,
            booking.time,
            booking.status,
            booking.created_at.strftime('%Y-%m-%d %H:%M') if booking.created_at else 'N/A'
        ])
    
    return output.getvalue()


def render_admin_dashboard():
    """Render the admin dashboard"""
    st.markdown("## 📊 Admin Dashboard")
    
    # Header with logout
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"**{config.clinic_name}** - Booking Management")
    with col2:
        if st.button("🚪 Logout", use_container_width=True):
            admin_logout()
    
    st.divider()
    
    # Filters
    st.markdown("### 🔍 Search & Filter")
    
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    
    with col1:
        search_term = st.text_input(
            "Search by name or email",
            placeholder="Enter name or email...",
            key="admin_search"
        )
    
    with col2:
        date_from = st.date_input(
            "From date",
            value=date.today() - timedelta(days=30),
            key="admin_date_from"
        )
    
    with col3:
        date_to = st.date_input(
            "To date",
            value=date.today() + timedelta(days=30),
            key="admin_date_to"
        )
    
    with col4:
        status_filter = st.selectbox(
            "Status",
            options=["All", "CONFIRMED", "PENDING", "CANCELLED", "COMPLETED"],
            key="admin_status"
        )
    
    # Fetch bookings
    try:
        db = get_database()
        
        status_enum = None
        if status_filter != "All":
            status_enum = BookingStatus(status_filter)
        
        bookings = db.search_bookings(
            search_term=search_term if search_term else None,
            date_from=date_from.strftime('%Y-%m-%d'),
            date_to=date_to.strftime('%Y-%m-%d'),
            status=status_enum
        )
        
    except DatabaseError as e:
        st.error(f"❌ Error loading bookings: {e}")
        bookings = []
    
    # Stats
    st.markdown("### 📈 Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total = len(bookings)
    confirmed = len([b for b in bookings if b.status == 'CONFIRMED'])
    pending = len([b for b in bookings if b.status == 'PENDING'])
    today_bookings = len([b for b in bookings if b.date == date.today().strftime('%Y-%m-%d')])
    
    with col1:
        st.metric("Total Bookings", total)
    with col2:
        st.metric("Confirmed", confirmed)
    with col3:
        st.metric("Pending", pending)
    with col4:
        st.metric("Today", today_bookings)
    
    st.divider()
    
    # Bookings table
    st.markdown("### 📋 Bookings")
    
    # Export button
    if bookings:
        csv_data = export_bookings_csv(bookings)
        st.download_button(
            label="📥 Export to CSV",
            data=csv_data,
            file_name=f"bookings_{date.today().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    if not bookings:
        st.info("No bookings found matching your criteria.")
    else:
        # Display as table
        for booking in bookings:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
                
                with col1:
                    st.markdown(f"**#{booking.id}**")
                
                with col2:
                    st.markdown(f"👤 **{booking.customer_name or 'N/A'}**")
                    st.caption(f"📧 {booking.customer_email or 'N/A'}")
                    st.caption(f"📞 {booking.customer_phone or 'N/A'}")
                
                with col3:
                    st.markdown(f"🏥 **{booking.booking_type}**")
                
                with col4:
                    st.markdown(f"📅 **{booking.date}**")
                    st.markdown(f"🕐 {booking.time}")
                
                with col5:
                    status = booking.status
                    if status == 'CONFIRMED':
                        st.success("✅ Confirmed")
                    elif status == 'PENDING':
                        st.warning("⏳ Pending")
                    elif status == 'CANCELLED':
                        st.error("❌ Cancelled")
                    else:
                        st.info(f"📌 {status}")
                
                st.divider()
    
    # Pagination info
    if bookings:
        st.caption(f"Showing {len(bookings)} booking(s)")


def render_admin_page():
    """Main admin page entry point"""
    st.set_page_config(
        page_title=f"Admin - {config.app_name}",
        page_icon="🔐",
        layout="wide"
    )
    
    # Custom styling
    st.markdown("""
    <style>
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
    }
    .stMetric label {
        color: rgba(255,255,255,0.8) !important;
    }
    .stMetric .metric-value {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    if not check_admin_auth():
        admin_login()
    else:
        render_admin_dashboard()


# For standalone testing
if __name__ == "__main__":
    render_admin_page()
