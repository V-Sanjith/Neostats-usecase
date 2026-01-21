"""
Configuration module for MedBook AI
Loads settings from Streamlit secrets with fallbacks
"""
import streamlit as st
from typing import Optional
import os

class Config:
    """Centralized configuration management"""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value with optional default"""
        try:
            return st.secrets.get(key, default)
        except Exception:
            return os.environ.get(key, default)
    
    # LLM Configuration
    @property
    def groq_api_key(self) -> str:
        return self.get_secret("GROQ_API_KEY", "")
    
    @property
    def gemini_api_key(self) -> str:
        return self.get_secret("GEMINI_API_KEY", "")
    
    @property
    def openai_api_key(self) -> str:
        return self.get_secret("OPENAI_API_KEY", "")
    
    # Legacy support for Grok (if needed)
    @property
    def grok_api_key(self) -> str:
        return self.get_secret("GROK_API_KEY", "")
    
    # Supabase Configuration
    @property
    def supabase_url(self) -> str:
        return self.get_secret("SUPABASE_URL", "")
    
    @property
    def supabase_anon_key(self) -> str:
        return self.get_secret("SUPABASE_ANON_KEY", "")
    
    @property
    def supabase_service_role_key(self) -> str:
        return self.get_secret("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Email Configuration
    @property
    def smtp_server(self) -> str:
        return self.get_secret("SMTP_SERVER", "smtp.gmail.com")
    
    @property
    def smtp_port(self) -> int:
        return int(self.get_secret("SMTP_PORT", "587"))
    
    @property
    def smtp_email(self) -> str:
        return self.get_secret("SMTP_EMAIL", "")
    
    @property
    def smtp_password(self) -> str:
        return self.get_secret("SMTP_PASSWORD", "")
    
    # Admin Configuration
    @property
    def admin_password(self) -> str:
        return self.get_secret("ADMIN_PASSWORD", "")
    
    # App Configuration
    @property
    def app_name(self) -> str:
        return self.get_secret("APP_NAME", "MedBook AI")
    
    @property
    def clinic_name(self) -> str:
        return self.get_secret("CLINIC_NAME", "HealthFirst Medical Center")
    
    @property
    def clinic_phone(self) -> str:
        return self.get_secret("CLINIC_PHONE", "+1-555-0123")
    
    @property
    def clinic_address(self) -> str:
        return self.get_secret("CLINIC_ADDRESS", "123 Health Street, Medical City")
    
    def validate(self) -> tuple[bool, list[str]]:
        """Validate that all required secrets are configured"""
        errors = []
        
        if not self.groq_api_key:
            errors.append("GROQ_API_KEY is required")
        if not self.supabase_url:
            errors.append("SUPABASE_URL is required")
        if not self.supabase_anon_key:
            errors.append("SUPABASE_ANON_KEY is required")
        if not self.smtp_email:
            errors.append("SMTP_EMAIL is required")
        if not self.smtp_password:
            errors.append("SMTP_PASSWORD is required")
        if not self.admin_password:
            errors.append("ADMIN_PASSWORD is required")
        
        return len(errors) == 0, errors


# Global config instance
config = Config()
