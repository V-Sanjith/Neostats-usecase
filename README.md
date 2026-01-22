# 🏥 MedBook AI - Medical Appointment Booking Chatbot

An AI-powered medical appointment booking assistant built with Streamlit, LangChain RAG, and Groq LLM.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
## 🎯 Features
- **Deployment link :** https://v-sanjith-neostats-usecase-appmain-k79qtt.streamlit.app/
- **🤖 AI-Powered Chat** - Natural language conversations using Groq's Llama 3.3 70B model
- **📅 Appointment Booking** - Multi-step conversational booking wizard
- **📄 RAG Q&A** - Upload PDFs and ask questions about clinic documents
- **📧 Email Notifications** - Automatic booking confirmations via email
- **🔐 Admin Dashboard** - Manage bookings with password-protected access
- **💾 Persistent Storage** - Supabase (PostgreSQL) for reliable data storage

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Chat UI   │  │ PDF Upload │  │Admin Panel │            │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
└────────┼───────────────┼───────────────┼────────────────────┘
         │               │               │
         ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                       AI LAYER                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Intent    │  │ Chat Logic │  │    RAG     │            │
│  │ Detection  │  │  (Memory)  │  │ (LangChain)│            │
│  └────────────┘  └─────┬──────┘  └─────┬──────┘            │
└────────────────────────┼───────────────┼────────────────────┘
                         │               │
    ┌────────────────────┼───────────────┼────────────────┐
    ▼                    ▼               ▼                ▼
┌────────┐        ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Groq  │        │ Supabase │    │ ChromaDB │    │HuggingFace│
│  LLM   │        │    DB    │    │ Vectors  │    │Embeddings │
└────────┘        └──────────┘    └──────────┘    └──────────┘
```

## 📁 Project Structure

```
MedBook-AI/
├── app/
│   ├── main.py              # Streamlit entry point
│   ├── chat_logic.py        # LLM & intent handling
│   ├── booking_flow.py      # Multi-step booking wizard
│   ├── rag_pipeline.py      # PDF processing & RAG
│   ├── admin_dashboard.py   # Admin management UI
│   ├── validators.py        # Input validation utilities
│   ├── rate_limiter.py      # Rate limiting for API calls
│   └── tools.py             # Utility functions
├── config/
│   └── config.py            # Centralized configuration
├── db/
│   ├── database.py          # Supabase CRUD operations
│   └── models.py            # Pydantic data models
├── utils/
│   ├── email_service.py     # SMTP email notifications
│   └── logging_config.py    # Logging setup
├── .streamlit/
│   └── secrets.toml         # API keys (not in repo)
├── requirements.txt         # Python dependencies
├── secrets.toml.template    # Template for secrets
└── README.md
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Supabase account (free tier works)
- Groq API key (free tier available)
- Gmail account for SMTP (with App Password)

### 1. Clone the Repository

```bash
git clone https://github.com/V-Sanjith/Neostats-usecase.git
cd Neostats-usecase
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Secrets

Create `.streamlit/secrets.toml` from the template:

```bash
cp secrets.toml.template .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml` with your credentials:

```toml
# LLM API Key (Groq - free tier available at console.groq.com)
GROQ_API_KEY = "your_groq_api_key"

# Supabase Configuration (free at supabase.com)
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your_anon_key"
SUPABASE_SERVICE_ROLE_KEY = "your_service_role_key"

# Email Configuration (Gmail with App Password)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "your_email@gmail.com"
SMTP_PASSWORD = "your_app_password"

# Admin Dashboard
ADMIN_PASSWORD = "admin@123"

# App Settings
APP_NAME = "MedBook AI"
CLINIC_NAME = "Your Clinic Name"
```

### 4. Set Up Supabase Database

Create a `bookings` table in Supabase with this SQL:

```sql
CREATE TABLE bookings (
    id SERIAL PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    booking_type VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    time TIME NOT NULL,
    notes TEXT,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. Run the Application

```bash
streamlit run app/main.py
```

The app will be available at `http://localhost:8501`

## 💡 Usage

### Booking an Appointment

1. Say "I want to book an appointment" or "Schedule a checkup"
2. Follow the conversational prompts:
   - Enter your name
   - Provide email address
   - Enter phone number
   - Select appointment type
   - Choose date
   - Pick time slot
3. Confirm booking
4. Receive email confirmation

### Asking Questions (RAG)

1. Upload PDF documents in the sidebar
2. Click "Process Documents"
3. Ask questions like:
   - "What is this document about?"
   - "What policies are mentioned?"
   - "Tell me about the clinic services"

### Admin Dashboard

1. Click "Admin" in the sidebar
2. Enter admin password
3. View all bookings
4. Confirm or cancel appointments

## 🔧 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Streamlit | Web UI |
| LLM | Groq (Llama 3.3 70B) | AI responses |
| Database | Supabase (PostgreSQL) | Data storage |
| Vector DB | ChromaDB | RAG embeddings |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) | Text embeddings |
| Email | SMTP (Gmail) | Notifications |

## 📊 Key Features Explained

### Intent Detection
Rule-based classification for routing:
- `BOOKING` - Schedule appointments
- `GREETING` - Hello, Hi responses
- `HELP` - Feature explanations
- `LOOKUP` - Check existing bookings
- `GENERAL` - RAG/LLM questions

### RAG Pipeline
1. **PDF Upload** → Extract text with pypdf
2. **Chunking** → 1000 chars with 200 overlap
3. **Embedding** → HuggingFace all-MiniLM-L6-v2
4. **Storage** → ChromaDB vector store
5. **Query** → Similarity search (top 8 results)
6. **Context Memory** → Session-based for follow-ups

### Booking Flow
Multi-step wizard with validation:
- Name: 2-50 characters
- Email: RFC 5322 format
- Phone: 10-15 digits
- Date: Future date within 90 days
- Time: 8:00 AM - 6:00 PM

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - feel free to use for personal or commercial projects.

## 👤 Author

**V-Sanjith**
- GitHub: [@V-Sanjith](https://github.com/V-Sanjith)

---

⭐ Star this repo if you find it helpful!
