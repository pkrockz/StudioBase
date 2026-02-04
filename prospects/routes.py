from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from datetime import datetime

from extensions import mongo
from . import prospects_bp

@prospects_bp.route("/prospects", methods=["GET", "POST"])
def prospects():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    if request.method == "POST":
        mongo.db.prospects.insert_one({
            "user_id": session["user_id"],
            "name": request.form.get("name"),
            "company": request.form.get("company"),
            "email": request.form.get("email"),
            "stage": "Discovery",
            "probability": 10,
            "value": float(request.form.get("value", 0)),
            "created_at": datetime.utcnow()
        })
        return redirect(url_for("prospects.prospects"))

    user_prospects = mongo.db.prospects.find({
        "user_id": session["user_id"]
    })

    return render_template(
        "prospects.html",
        prospects=user_prospects
    )


@prospects_bp.route("/prospects/update_stage/<prospect_id>", methods=["POST"])
def update_prospect_stage(prospect_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    new_stage = request.form.get("stage")

    probability_map = {
        "Discovery": 10,
        "Proposal Sent": 50,
        "Negotiating": 75,
        "Verbal Agreement": 90,
        "Closed Lost": 0,
        "Won": 100
    }

    mongo.db.prospects.update_one(
        {"_id": ObjectId(prospect_id), "user_id": session["user_id"]},
        {"$set": {
            "stage": new_stage,
            "probability": probability_map.get(new_stage, 10)
        }}
    )

    return redirect(url_for("prospects.prospects"))


@prospects_bp.route("/prospects/update_value/<prospect_id>", methods=["POST"])
def update_prospect_value(prospect_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    mongo.db.prospects.update_one(
        {"_id": ObjectId(prospect_id), "user_id": session["user_id"]},
        {"$set": {
            "value": float(request.form.get("value", 0))
        }}
    )

    return redirect(url_for("prospects.prospects"))


@prospects_bp.route("/prospects/delete/<prospect_id>")
def delete_prospect(prospect_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    mongo.db.prospects.delete_one({
        "_id": ObjectId(prospect_id),
        "user_id": session["user_id"]
    })

    return redirect(url_for("prospects.prospects"))

@prospects_bp.route("/prospects/convert/<prospect_id>")
def convert_prospect(prospect_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    prospect = mongo.db.prospects.find_one({
        "_id": ObjectId(prospect_id),
        "user_id": session["user_id"]
    })

    if prospect:
        mongo.db.clients.insert_one({
            "user_id": session["user_id"],
            "prospect_id": prospect["_id"],
            "name": prospect["name"],
            "company": prospect["company"],
            "email": prospect["email"],
            "contract_value": prospect.get("value", 0),
            "status": "Active",
            "billing_terms": "50% Upfront",
            "created_at": datetime.utcnow()
        })

        mongo.db.prospects.update_one(
            {"_id": prospect["_id"]},
            {"$set": {"stage": "Won", "probability": 100}}
        )

    return redirect(url_for("clients.clients"))
