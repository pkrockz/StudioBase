from flask_pymongo import PyMongo
from authlib.integrations.flask_client import OAuth

mongo = PyMongo()
oauth = OAuth()