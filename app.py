import os
import json
from datetime import datetime
from flask import Flask, render_template, session, redirect, url_for, request
from dotenv import load_dotenv
from bson.objectid import ObjectId
import google.generativeai as genai

# Load environment variables
load_dotenv() 

from config import Config
from extensions import mongo, oauth

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    mongo.init_app(app)
    oauth.init_app(app)

    # AI setup
    genai.configure(api_key=app.config.get("GEMINI_API_KEY"))

    # --- Custom Filters (Fixes Date Crashes) ---
    @app.template_filter('date_format')
    def date_format(value, format='%Y-%m-%d'):
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, datetime):
            return value.strftime(format)
        return value

    # --- OAuth Setup ---
    global github, google

    github = oauth.register(
        name='github',
        client_id=app.config.get("GITHUB_CLIENT_ID"),
        client_secret=app.config.get("GITHUB_CLIENT_SECRET"),
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'user:email'},
    )

    google = oauth.register(
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
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
