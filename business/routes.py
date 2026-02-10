from flask import render_template, session, redirect, url_for, request
from datetime import datetime
from extensions import mongo
from . import business_bp

@business_bp.route("/business", methods=["GET", "POST"])
def business_profile():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    profile = mongo.db.business_profile.find_one({
        "user_id": session["user_id"]
    })

    if request.method == "POST":
        data = {
            "user_id": session["user_id"],
            "business_name": request.form.get("business_name"),
            "address": request.form.get("address"),
            "phone": request.form.get("phone"),
            "gstin": request.form.get("gstin"),
            "created_at": datetime.utcnow()
        }

        if profile:
            mongo.db.business_profile.update_one(
                {"_id": profile["_id"]},
                {"$set": data}
            )
        else:
            mongo.db.business_profile.insert_one(data)

        return redirect(url_for("invoices.invoices"))

    return render_template(
        "business_profile.html",
        profile=profile
    )
