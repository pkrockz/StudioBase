from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from datetime import datetime

from extensions import mongo
from . import clients_bp


@clients_bp.route("/clients", methods=["GET", "POST"])
def clients():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        mongo.db.clients.insert_one({
            "user_id": session["user_id"],
            "name": request.form.get("name"),
            "company": request.form.get("company"),
            "email": request.form.get("email"),
            "contract_value": float(request.form.get("contract_value", 0)),
            "status": "Active",
            "created_at": datetime.utcnow()
        })
        return redirect(url_for("clients.clients"))

    user_clients = mongo.db.clients.find({
        "user_id": session["user_id"]
    })

    return render_template(
        "clients.html",
        clients=user_clients
    )


@clients_bp.route("/clients/delete/<client_id>")
def delete_client(client_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    client = mongo.db.clients.find_one({
        "_id": ObjectId(client_id),
        "user_id": session["user_id"]
    })

    if not client:
        return redirect(url_for("clients.clients"))

    # --- CASCADE DELETE (INTENTIONAL & ORDERED) ---

    # 1. Delete invoices tied to this client name
    mongo.db.invoices.delete_many({
        "user_id": session["user_id"],
        "client_name": client["name"]
    })

    # 2. Find projects for this client
    projects = mongo.db.projects.find({
        "user_id": session["user_id"],
        "client_id": ObjectId(client_id)
    })

    # 3. Delete tasks for each project
    for project in projects:
        mongo.db.tasks.delete_many({
            "user_id": session["user_id"],
            "project_id": project["_id"]
        })

    # 4. Delete projects
    mongo.db.projects.delete_many({
        "user_id": session["user_id"],
        "client_id": ObjectId(client_id)
    })

    # 5. Delete client
    mongo.db.clients.delete_one({
        "_id": ObjectId(client_id),
        "user_id": session["user_id"]
    })

    return redirect(url_for("clients.clients"))
