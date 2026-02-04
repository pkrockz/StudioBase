from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from extensions import mongo
from datetime import datetime
from . import invoices_bp

@invoices_bp.route("/invoices", methods=["GET", "POST"])
def invoices():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        invoice_number = f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(ObjectId())[-4:]}"
        mongo.db.invoices.insert_one({
            "user_id": session["user_id"],
            "invoice_number": invoice_number,
            "client_name": request.form.get("client_name"),
            "project_title": request.form.get("project_title"),
            "amount": float(request.form.get("amount", 0)),
            "due_date": request.form.get("due_date"),
            "status": "Unpaid",
            "created_at": datetime.utcnow()
        })
        return redirect(url_for("invoices.invoices"))

    invoices = mongo.db.invoices.find({
        "user_id": session["user_id"]
    })

    clients = mongo.db.clients.find({
        "user_id": session["user_id"]
    })

    projects = mongo.db.projects.find({
        "user_id": session["user_id"]
    })

    return render_template(
        "invoices.html",
        invoices=invoices,
        clients=clients,
        projects=projects
    )

@invoices_bp.route("/invoices/<invoice_id>/view")
def view_invoice(invoice_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    invoice = mongo.db.invoices.find_one({
        "_id": ObjectId(invoice_id),
        "user_id": session["user_id"]
    })

    user = mongo.db.users.find_one({
        "_id": ObjectId(session["user_id"])
    })

    return render_template(
        "invoice_view.html",
        invoice=invoice,
        user=user
    )

@invoices_bp.route("/invoices/<invoice_id>/pay")
def mark_invoice_paid(invoice_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    mongo.db.invoices.update_one(
        {"_id": ObjectId(invoice_id), "user_id": session["user_id"]},
        {"$set": {"status": "Paid"}}
    )

    return redirect(url_for("invoices.invoices"))

@invoices_bp.route("/invoices/<invoice_id>/delete")
def delete_invoice(invoice_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    mongo.db.invoices.delete_one({
        "_id": ObjectId(invoice_id),
        "user_id": session["user_id"]
    })

    return redirect(url_for("invoices.invoices"))