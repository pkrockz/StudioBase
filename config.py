import os
from dotenv import load_dotenv

load_dotenv() 
class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    MONGO_URI = os.getenv("MONGO_URI")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")