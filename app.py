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

    @app.route('/dashboard')
    def dashboard():
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        user_id = session['user_id']
        today_str = datetime.utcnow().strftime('%Y-%m-%d')

        # 1. Active Projects Count
        active_projects_count = mongo.db.projects.count_documents({
            "user_id": user_id, "status": {"$ne": "Completed"}
        })

        # 2. Pipeline Value
        pipeline_cursor = mongo.db.prospects.aggregate([
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": None, "total": {"$sum": "$value"}}}
        ])
        pipeline_val = list(pipeline_cursor)
        pipeline_total = pipeline_val[0]['total'] if pipeline_val else 0

        # 3. Pending Tasks
        pending_tasks_count = mongo.db.tasks.count_documents({
            "user_id": user_id, "status": "Pending"
        })

        # 4. Overdue Invoices
        overdue_count = mongo.db.invoices.count_documents({
            "user_id": user_id, "status": "Unpaid", "due_date": {"$lt": today_str}
        })

        # 5. Urgent Leads (Oldest cold leads)
        urgent_leads = mongo.db.leads.find({
            "user_id": user_id, "status": "Cold"
        }).sort("created_at", 1).limit(5)

        # 6. Active Projects List WITH PROGRESS CALCULATION
        # Fetch cursor first
        projects_cursor = mongo.db.projects.find({
            "user_id": user_id, "status": {"$ne": "Completed"}
        }).sort("deadline", 1).limit(5)
        
        active_projects = []
        for p in projects_cursor:
            # Calculate Progress
            total_tasks = mongo.db.tasks.count_documents({"project_id": p['_id']})
            done_tasks = mongo.db.tasks.count_documents({"project_id": p['_id'], "status": "Done"})
            
            if total_tasks > 0:
                progress = int((done_tasks / total_tasks) * 100)
            else:
                progress = 0
                
            # Attach data to the project object for the template
            p['progress'] = progress
            p['tasks_done'] = done_tasks
            p['tasks_total'] = total_tasks
            active_projects.append(p)
        
        return render_template('dashboard.html', 
                            username=session.get('username'),
                            active_projects_count=active_projects_count,
                            pipeline_total=pipeline_total,
                            pending_tasks_count=pending_tasks_count,
                            overdue_count=overdue_count,
                            urgent_leads=urgent_leads,
                            active_projects=active_projects)

    # --- LEADS ROUTES ---

    @app.route('/leads', methods=['GET', 'POST'])
    def leads():
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        if request.method == 'POST':
            # Add New Lead
            mongo.db.leads.insert_one({
                "user_id": session['user_id'],
                "name": request.form.get('name'),
                "company": request.form.get('company'),
                "email": request.form.get('email'),
                "source": request.form.get('source'),
                "status": "Cold",
                "created_at": datetime.utcnow()
            })
            return redirect(url_for('leads'))

        user_leads = mongo.db.leads.find({
            "user_id": session['user_id'],
            "status": {"$ne": "Converted"} 
        })
        return render_template('leads.html', leads=user_leads)

    @app.route('/leads/update_status/<lead_id>', methods=['POST'])
    def update_lead_status(lead_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        new_status = request.form.get('status')
        mongo.db.leads.update_one(
            {"_id": ObjectId(lead_id), "user_id": session['user_id']},
            {"$set": {"status": new_status}}
        )
        return redirect(url_for('leads'))

    @app.route('/convert_lead/<lead_id>')
    def convert_lead(lead_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        lead = mongo.db.leads.find_one({"_id": ObjectId(lead_id), "user_id": session['user_id']})
        
        if lead:
            mongo.db.prospects.insert_one({
                "user_id": session['user_id'],
                "lead_id": lead['_id'],
                "name": lead['name'],
                "company": lead['company'],
                "email": lead['email'],
                "source": lead.get('source', 'Unknown'),
                "stage": "Proposal Sent",
                "probability": 50,
                "value": 0,
                "created_at": datetime.utcnow()
            })
            
            mongo.db.leads.update_one({"_id": ObjectId(lead_id)}, {"$set": {"status": "Converted"}})
            
        return redirect(url_for('prospects'))

    @app.route('/leads/delete/<lead_id>')
    def delete_lead(lead_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        mongo.db.leads.delete_one({"_id": ObjectId(lead_id), "user_id": session['user_id']})
        return redirect(url_for('leads'))

    # --- PROSPECTS ROUTES ---

    @app.route('/prospects', methods=['GET', 'POST'])
    def prospects():
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        if request.method == 'POST':
            mongo.db.prospects.insert_one({
                "user_id": session['user_id'],
                "name": request.form.get('name'),
                "company": request.form.get('company'),
                "email": request.form.get('email'),
                "stage": "Discovery",
                "probability": 10,
                "value": float(request.form.get('value', 0)),
                "created_at": datetime.utcnow()
            })
            return redirect(url_for('prospects'))
            
        user_prospects = mongo.db.prospects.find({"user_id": session['user_id']})
        return render_template('prospects.html', prospects=user_prospects)

    @app.route('/prospects/update_stage/<prospect_id>', methods=['POST'])
    def update_prospect_stage(prospect_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        new_stage = request.form.get('stage')
        
        new_prob = 10
        if new_stage == "Proposal Sent": new_prob = 50
        elif new_stage == "Negotiating": new_prob = 75
        elif new_stage == "Verbal Agreement": new_prob = 90
        elif new_stage == "Closed Lost": new_prob = 0
        
        mongo.db.prospects.update_one(
            {"_id": ObjectId(prospect_id), "user_id": session['user_id']},
            {"$set": {"stage": new_stage, "probability": new_prob}}
        )
        return redirect(url_for('prospects'))

    @app.route('/prospects/update_value/<prospect_id>', methods=['POST'])
    def update_prospect_value(prospect_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        new_value = float(request.form.get('value', 0))
        
        mongo.db.prospects.update_one(
            {"_id": ObjectId(prospect_id), "user_id": session['user_id']},
            {"$set": {"value": new_value}}
        )
        return redirect(url_for('prospects'))

    @app.route('/convert_prospect/<prospect_id>')
    def convert_prospect(prospect_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        # 1. Get the Prospect Data
        prospect = mongo.db.prospects.find_one({"_id": ObjectId(prospect_id), "user_id": session['user_id']})
        
        if prospect:
            # 2. Create the CLIENT (Inherit data + VALUE)
            mongo.db.clients.insert_one({
                "user_id": session['user_id'],
                "prospect_id": prospect['_id'],
                "name": prospect['name'],
                "company": prospect['company'],
                "email": prospect['email'],
                # NEW: Inherit the value from the prospect
                "contract_value": prospect.get('value', 0), 
                "status": "Active",
                "billing_terms": "50% Upfront",
                "created_at": datetime.utcnow()
            })
            
            # 3. Mark Prospect as "Won"
            mongo.db.prospects.update_one(
                {"_id": ObjectId(prospect_id)}, 
                {"$set": {"stage": "Won", "probability": 100}}
            )
            
        return redirect(url_for('clients'))

    @app.route('/prospects/delete/<prospect_id>')
    def delete_prospect(prospect_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        mongo.db.prospects.delete_one({"_id": ObjectId(prospect_id), "user_id": session['user_id']})
        return redirect(url_for('prospects'))

    # --- CLIENTS ROUTES ---

    @app.route('/clients', methods=['GET', 'POST'])
    def clients():
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        if request.method == 'POST':
            mongo.db.clients.insert_one({
                "user_id": session['user_id'],
                "name": request.form.get('name'),
                "company": request.form.get('company'),
                "email": request.form.get('email'),
                "contract_value": float(request.form.get('contract_value', 0)),
                "billing_terms": request.form.get('billing_terms'),
                "status": "Active",
                "created_at": datetime.utcnow()
            })
            return redirect(url_for('clients'))

        user_clients = mongo.db.clients.find({"user_id": session['user_id']})
        return render_template('clients.html', clients=user_clients)

    @app.route('/clients/delete/<client_id>')
    def delete_client(client_id):
        if 'user_id' not in session: return redirect(url_for('auth.index'))
        
        # 1. Identify the Client
        client = mongo.db.clients.find_one({"_id": ObjectId(client_id), "user_id": session['user_id']})
        
        if client:
            # 2. Delete all Invoices linked to this Client Name
            # (Since invoices currently link by name string)
            mongo.db.invoices.delete_many({
                "user_id": session['user_id'], 
                "client_name": client['name']
            })

            # 3. Find all Projects linked to this Client ID
            projects = mongo.db.projects.find({
                "user_id": session['user_id'], 
                "client_id": ObjectId(client_id)
            })
            
            # 4. Delete Tasks for each Project
            for p in projects:
                mongo.db.tasks.delete_many({
                    "user_id": session['user_id'],
                    "project_id": p['_id']
                })
                
            # 5. Delete the Projects themselves
            mongo.db.projects.delete_many({
                "user_id": session['user_id'], 
                "client_id": ObjectId(client_id)
            })

            # 6. Finally, Delete the Client
            mongo.db.clients.delete_one({
                "_id": ObjectId(client_id), 
                "user_id": session['user_id']
            })

        return redirect(url_for('clients'))

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
