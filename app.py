import os
from datetime import datetime
from flask import Flask
from dotenv import load_dotenv
import google.generativeai as genai

if os.getenv("FLASK_ENV") != "production":
    load_dotenv()

from config import Config
from extensions import mongo, oauth

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    @app.template_filter("date_format")
    def date_format(value, format='%Y-%m-%d'):
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return value.strftime(format)
        return value

    @app.template_filter("currency")
    def currency(amount):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return ""
        return f"₹{amount:,.2f}"

    @app.template_filter("gst")
    def gst(amount):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {}

        cgst_rate = app.config.get("CGST_RATE", 0.09)
        sgst_rate = app.config.get("SGST_RATE", 0.09)

        cgst = amount * cgst_rate
        sgst = amount * sgst_rate

        return {
            "base": amount,
            "cgst": cgst,
            "sgst": sgst,
            "total": amount + cgst + sgst
        }

    # EXTENSIONS 
    mongo.init_app(app)
    oauth.init_app(app)

    # AI setup
    genai.configure(api_key=app.config.get("GEMINI_API_KEY"))

    # OAuth Setup 
    oauth.register(
        name='github',
        client_id=app.config.get("GITHUB_CLIENT_ID"),
        client_secret=app.config.get("GITHUB_CLIENT_SECRET"),
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )

    oauth.register(
        name='google',
        client_id=app.config.get("GOOGLE_CLIENT_ID"),
        client_secret=app.config.get("GOOGLE_CLIENT_SECRET"),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # --- ROUTES ---
    from auth import auth_bp
    app.register_blueprint(auth_bp)

    # --- DASHBOARD ---

    from dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    # --- LEADS ROUTES ---

    from leads import leads_bp
    app.register_blueprint(leads_bp)

    # --- PROSPECTS ROUTES ---

    from prospects import prospects_bp
    app.register_blueprint(prospects_bp)

    # --- CLIENTS ROUTES ---

    from clients import clients_bp
    app.register_blueprint(clients_bp)

    # --- PROJECTS & AI ROUTES ---

    from projects import projects_bp
    app.register_blueprint(projects_bp)

    # --- INVOICE ROUTES ---

    from invoices import invoices_bp
    app.register_blueprint(invoices_bp)

    # --- BUSINESS INFO ---
    from business import business_bp
    app.register_blueprint(business_bp)

    return app

app = create_app()

if __name__ == '__main__':
    app.run()
