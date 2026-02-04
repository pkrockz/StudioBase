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

    @app.route('/projects', methods=['GET', 'POST'])
    def projects():
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        if request.method == 'POST':
            client_id = request.form.get('client_id')
            client_obj = mongo.db.clients.find_one({"_id": ObjectId(client_id)})
            
            project_id = mongo.db.projects.insert_one({
                "user_id": session['user_id'],
                "client_id": ObjectId(client_id),
                "client_name": client_obj['name'],
                "title": request.form.get('title'),
                "description": request.form.get('description'),
                "status": "Planning",
                "deadline": request.form.get('deadline'),
                "created_at": datetime.utcnow()
            }).inserted_id
            
            if request.form.get('use_ai') == 'on':
                return generate_tasks(project_id, request.form.get('description'))
            
            # If not using AI, go straight to detail page to add tasks manually
            return redirect(url_for('project_detail', project_id=project_id))

        clients = mongo.db.clients.find({"user_id": session['user_id']}) 
        user_projects = mongo.db.projects.find({"user_id": session['user_id']})
        
        return render_template('projects.html', projects=user_projects, clients=clients)

    def generate_tasks(project_id, description):
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        You are a technical project manager. Break this description into a list of 
        3-5 specific technical tasks. 
        Strict Rules:
        1. Return ONLY a valid JSON array.
        2. Do not write "Here is the json" or any other text.
        3. Use double quotes for keys and values.
        Format example:
        [{{"task": "Setup MongoDB schema", "hours": 2}}, {{"task": "Configure Flask routes", "hours": 4}}]
        Project Description: {description}
        """
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            print(f"DEBUG AI: {text}") 

            start_index = text.find('[')
            end_index = text.rfind(']')
            if start_index != -1 and end_index != -1:
                json_str = text[start_index : end_index + 1]
                tasks = json.loads(json_str)
                for t in tasks:
                    mongo.db.tasks.insert_one({
                        "user_id": session['user_id'],
                        "project_id": ObjectId(project_id),
                        "description": t.get('task') or t.get('description'),
                        "hours": t.get('hours', 1),
                        "status": "Pending"
                    })
        except Exception as e:
            print(f"AI Error: {e}")
        return redirect(url_for('project_detail', project_id=project_id))

    @app.route('/project/<project_id>')
    def project_detail(project_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
        # Sort tasks so "Pending" appear first, then "Done"
        tasks = mongo.db.tasks.find({"project_id": ObjectId(project_id)}).sort("status", -1)
        return render_template('project_detail.html', project=project, tasks=tasks)

    @app.route('/projects/delete/<project_id>')
    def delete_project(project_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        # FIX: Cascade Delete - Delete tasks first, then the project
        mongo.db.tasks.delete_many({"project_id": ObjectId(project_id)})
        mongo.db.projects.delete_one({"_id": ObjectId(project_id), "user_id": session['user_id']})
        
        return redirect(url_for('projects'))

    @app.route('/project/<project_id>/add_task', methods=['POST'])
    def add_task(project_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        mongo.db.tasks.insert_one({
            "user_id": session['user_id'],
            "project_id": ObjectId(project_id),
            "description": request.form.get('description'),
            "hours": float(request.form.get('hours', 0)),
            "status": "Pending"
        })
        return redirect(url_for('project_detail', project_id=project_id))

    @app.route('/task/<task_id>/edit', methods=['POST'])
    def edit_task(task_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        mongo.db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "description": request.form.get('description'),
                "hours": float(request.form.get('hours', 0))
            }}
        )
        # Get project_id from hidden field to redirect back correctly
        project_id = request.form.get('project_id')
        return redirect(url_for('project_detail', project_id=project_id))

    @app.route('/task/<task_id>/toggle')
    def toggle_task(task_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
        new_status = "Done" if task['status'] == "Pending" else "Pending"
        
        mongo.db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"status": new_status}}
        )
        return redirect(url_for('project_detail', project_id=task['project_id']))

    @app.route('/project/<project_id>/complete')
    def complete_project(project_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        # 1. Update Project Status
        project = mongo.db.projects.find_one({"_id": ObjectId(project_id)})
        mongo.db.projects.update_one(
            {"_id": ObjectId(project_id), "user_id": session['user_id']},
            {"$set": {"status": "Completed"}}
        )
        
        # 2. Redirect to Invoices with "pre-fill" data in the URL
        # We pass the names so the Invoice form can auto-select them
        return redirect(url_for('invoices', 
                            prefill_client=project['client_name'], 
                            prefill_project=project['title']))

    @app.route('/task/<task_id>/delete')
    def delete_task(task_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        task = mongo.db.tasks.find_one({"_id": ObjectId(task_id)})
        project_id = task['project_id']
        
        mongo.db.tasks.delete_one({"_id": ObjectId(task_id)})
        return redirect(url_for('project_detail', project_id=project_id))

    # --- INVOICE ROUTES ---

    @app.route('/invoices', methods=['GET', 'POST'])
    def invoices():
        # ... [Keep existing invoice creation logic] ...
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        if request.method == 'POST':
            inv_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(ObjectId())[-4:]}"
            mongo.db.invoices.insert_one({
                "user_id": session['user_id'],
                "invoice_number": inv_number,
                "client_name": request.form.get('client_name'),
                "project_title": request.form.get('project_title'),
                "amount": float(request.form.get('amount')),
                "due_date": request.form.get('due_date'),
                "status": "Unpaid",
                "created_at": datetime.utcnow()
            })
            return redirect(url_for('invoices'))

        user_invoices = mongo.db.invoices.find({"user_id": session['user_id']})
        clients = mongo.db.clients.find({"user_id": session['user_id']}) 
        projects = mongo.db.projects.find({"user_id": session['user_id']})
        return render_template('invoices.html', invoices=user_invoices, clients=clients, projects=projects)

    @app.route('/invoice/<invoice_id>/pay')
    def mark_invoice_paid(invoice_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        # 1. Mark this invoice as Paid
        mongo.db.invoices.update_one(
            {"_id": ObjectId(invoice_id)}, 
            {"$set": {"status": "Paid", "paid_date": datetime.utcnow()}}
        )
        
        # 2. AUTO-DELETE LOGIC
        # Retrieve the invoice to find out who the client is
        invoice = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
        if invoice:
            client_name = invoice.get('client_name')
            
            # Check if this client has ANY remaining "Unpaid" invoices
            unpaid_count = mongo.db.invoices.count_documents({
                "user_id": session['user_id'],
                "client_name": client_name,
                "status": "Unpaid"
            })
            
            # If no unpaid invoices remain, delete the client from the active list
            if unpaid_count == 0:
                mongo.db.clients.delete_one({
                    "user_id": session['user_id'], 
                    "name": client_name
                })
                
        return redirect(url_for('invoices'))

    @app.route('/invoice/<invoice_id>/view')
    def view_invoice(invoice_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        invoice = mongo.db.invoices.find_one({"_id": ObjectId(invoice_id)})
        user = mongo.db.users.find_one({"_id": ObjectId(session['user_id'])})
        return render_template('invoice_view.html', invoice=invoice, user=user)

    @app.route('/invoices/delete/<invoice_id>')
    def delete_invoice(invoice_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        mongo.db.invoices.delete_one({"_id": ObjectId(invoice_id), "user_id": session['user_id']})
        return redirect(url_for('invoices'))
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
