from flask_pymongo import PyMongo
from authlib.integrations.flask_client import OAuth

mongo = PyMongo()
oauth = OAuth()
# genai_client = genai.configure(api_key=os.getenv("GEMINI_API_KEY"))