from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from datetime import datetime

from extensions import mongo
from . import leads_bp


@leads_bp.route("/leads", methods=["GET", "POST"])
def leads():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        mongo.db.leads.insert_one({
            "user_id": session["user_id"],
            "name": request.form.get("name"),
            "company": request.form.get("company"),
            "email": request.form.get("email"),
            "source": request.form.get("source"),
            "status": "Cold",
            "created_at": datetime.utcnow(),
        })
        return redirect(url_for("leads.leads"))

    user_leads = mongo.db.leads.find({
        "user_id": session["user_id"],
        "status": {"$ne": "Converted"},
    })

    return render_template("leads.html", leads=user_leads)


@leads_bp.route("/leads/update_status/<lead_id>", methods=["POST"])
def update_lead_status(lead_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    new_status = request.form.get("status")

    mongo.db.leads.update_one(
        {"_id": ObjectId(lead_id), "user_id": session["user_id"]},
        {"$set": {"status": new_status}},
    )

    return redirect(url_for("leads.leads"))


@leads_bp.route("/convert_lead/<lead_id>")
def convert_lead(lead_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    lead = mongo.db.leads.find_one({
        "_id": ObjectId(lead_id),
        "user_id": session["user_id"],
    })

    if lead:
        mongo.db.prospects.insert_one({
            "user_id": session["user_id"],
            "lead_id": lead["_id"],
            "name": lead["name"],
            "company": lead["company"],
            "email": lead["email"],
            "source": lead.get("source", "Unknown"),
            "stage": "Proposal Sent",
            "probability": 50,
            "value": 0,
            "created_at": datetime.utcnow(),
        })

        mongo.db.leads.update_one(
            {"_id": lead["_id"]},
            {"$set": {"status": "Converted"}},
        )

    return redirect(url_for("prospects.prospects"))


@leads_bp.route("/leads/delete/<lead_id>")
def delete_lead(lead_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    mongo.db.leads.delete_one({
        "_id": ObjectId(lead_id),
        "user_id": session["user_id"],
    })

    return redirect(url_for("leads.leads"))