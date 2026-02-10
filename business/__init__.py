from flask import Blueprint

business_bp = Blueprint("business", __name__)

from . import routes
