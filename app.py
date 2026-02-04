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

    # @app.route('/invoices', methods=['GET', 'POST'])
    # def invoices():
    #     # ... [Keep existing invoice creation logic] ...
    #     if 'user_id' not in session: return redirect(url_for('auth.index'))
    #     if request.method == 'POST':
    #         inv_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(ObjectId())[-4:]}"
    #         mongo.db.invoices.insert_one({
    #             "user_id": session['user_id'],
    #             "invoice_number": inv_number,
    #             "client_name": request.form.get('client_name'),
    #             "project_title": request.form.get('project_title'),
    #             "amount": float(request.form.get('amount')),
    #             "due_date": request.form.get('due_date'),
    #             "status": "Unpaid",
    #             "created_at": datetime.utcnow()
    #         })
    #         return redirect(url_for('invoices'))

    #     user_invoices = mongo.db.invoices.find({"user_id": session['user_id']})
    #     clients = mongo.db.clients.find({"user_id": session['user_id']}) 
    #     projects = mongo.db.projects.find({"user_id": session['user_id']})
    #     return render_template('invoices.html', invoices=user_invoices, clients=clients, projects=projects)

    # @app.route('/invoice/<invoice_id>/pay')
    # def mark_invoice_paid(invoice_id):
    #     if 'user_id' not in session: return redirect(url_for('auth.index'))
        
    #     # 1. Mark this invoice as Paid
    #     mongo.db.invoices.update_one(
    #         {"_id": ObjectId(invoice_id)}, 
    #         {"$set": {"status": "Paid", "paid_date": datetime.utcnow()}}
    #     )
        
    #     # 2. AUTO-DELETE LOGIC
    #     # Retrieve the invoice to find out who the client is
    #     invoice = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
    #     if invoice:
    #         client_name = invoice.get('client_name')
            
    #         # Check if this client has ANY remaining "Unpaid" invoices
    #         unpaid_count = mongo.db.invoices.count_documents({
    #             "user_id": session['user_id'],
    #             "client_name": client_name,
    #             "status": "Unpaid"
    #         })
            
    #         # If no unpaid invoices remain, delete the client from the active list
    #         if unpaid_count == 0:
    #             mongo.db.clients.delete_one({
    #                 "user_id": session['user_id'], 
    #                 "name": client_name
    #             })
                
    #     return redirect(url_for('invoices'))

    # @app.route('/invoice/<invoice_id>/view')
    # def view_invoice(invoice_id):
    #     if 'user_id' not in session: return redirect(url_for('auth.index'))
    #     invoice = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
    #     user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
    #     return render_template('invoice_view.html', invoice=invoice, user=user)

    # @app.route('/invoices/delete/<invoice_id>')
    # def delete_invoice(invoice_id):
    #     if 'user_id' not in session: return redirect(url_for('auth.index'))
    #     mongo.db.invoices.delete_one({"_id": ObjectId(invoice_id), "user_id": session['user_id']})
    #     return redirect(url_for('invoices'))
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
