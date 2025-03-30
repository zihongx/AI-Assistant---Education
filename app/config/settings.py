import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Base directory - used for path resolution
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")

# API Configuration
API_URL = os.getenv('API_URL', 'http://127.0.0.1:5000')

# Database Settings
DB_PATH = os.path.join(DATA_DIR, "appointments.db")
os.makedirs(DATA_DIR, exist_ok=True)  # Ensure data directory exists

# Data file paths
PRICES_CSV_PATH = os.path.join(DATA_DIR, "prices.csv")
BASIC_INFO_PATH = os.path.join(DATA_DIR, "Basic_information.md")

# OpenAI API Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key is missing. Please set it in .env")

# Model Configuration
MODEL_CONFIG = {
    'MODEL_NAME': 'gpt-4o-mini',  # or 'gpt-3.5-turbo'
    'CONFIDENCE_THRESHOLD': 0.7,
    'TEMPERATURE': 0.7,
    'MAX_TOKENS': 1000
}

# Vector Store Settings 
VECTOR_STORE_CONFIG = {
    'CHUNK_SIZE': 512,
    'CHUNK_OVERLAP': 100,
    'RERANKER_MODEL': 'BAAI/bge-reranker-large',
    'TOP_K': 5,
    'TOP_N': 3
}

# SMTP Settings for email
SMTP_CONFIG = {
    "server": "smtp.gmail.com",
    "port": 587,
    "email": os.getenv("EMAIL_ADDRESS"),
    "password": os.getenv("EMAIL_PASSWORD"),
    "admin_email": "newturbony@gmail.com"
}

# System prompt
try:
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        SYSTEM_PROMPT = f.read().strip()
except FileNotFoundError:
    SYSTEM_PROMPT = """I am an AI assistant for New Turbo Education, a tutoring center specializing in SAT, AP, ACT, SHSAT, TOEFL, ESL, and college admissions consulting. I provide bilingual responses in English and Chinese to help both parents and students. I aim to be professional, friendly and helpful in answering questions about courses, tutoring, pricing, schedules and other education-related topics."""

# Available Time Slots
AVAILABLE_SLOTS = {
    "Monday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Tuesday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Wednesday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Thursday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Friday": ["10:00", "11:00", "14:00", "15:00", "16:00"],
    "Saturday": ["10:00", "11:00", "14:00"],
    "Sunday": ["10:00", "11:00", "14:00", "15:00"]
} 