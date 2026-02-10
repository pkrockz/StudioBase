from flask import render_template, session, redirect, url_for, request
from extensions import mongo
from datetime import datetime
from . import settings_bp

@settings_bp.route("/settings/business", methods=["GET", "POST"])
def business_settings():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    existing = mongo.db.business_profiles.find_one({
        "user_id": session["user_id"]
    })

    if request.method == "POST":
        data = {
            "user_id": session["user_id"],
            "business_name": request.form.get("business_name"),
            "address": request.form.get("address"),
            "phone": request.form.get("phone"),
            "gstin": request.form.get("gstin"),
            "updated_at": datetime.utcnow()
        }

        if existing:
            mongo.db.business_profiles.update_one(
                {"_id": existing["_id"]},
                {"$set": data}
            )
        else:
            data["created_at"] = datetime.utcnow()
            mongo.db.business_profiles.insert_one(data)

        return redirect(url_for("settings.business_settings"))

    return render_template(
        "business_settings.html",
        business=existing
    )
