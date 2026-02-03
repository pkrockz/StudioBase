from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from datetime import datetime

from extensions import mongo, oauth
from . import auth_bp

# OAuth clients will be registered in app factory
github = oauth.github
google = oauth.google


@auth_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html")


@auth_bp.route("/login/github")
def login_github():
    redirect_uri = url_for("auth.authorize_github", _external=True)
    return github.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google")
def login_google():
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route("/authorize/github")
def authorize_github():
    token = github.authorize_access_token()
    user_info = github.get("user", token=token).json()

    user_data = {
        "oauth_id": str(user_info["id"]),
        "provider": "github",
        "username": user_info["login"],
        "email": user_info.get("email"),
        "avatar_url": user_info["avatar_url"],
    }
    return handle_login(user_data)


@auth_bp.route("/authorize/google")
def authorize_google():
    token = google.authorize_access_token()
    user_info = token.get("userinfo")

    user_data = {
        "oauth_id": user_info["sub"],
        "provider": "google",
        "username": user_info["name"],
        "email": user_info["email"],
        "avatar_url": user_info["picture"],
    }
    return handle_login(user_data)


def handle_login(data):
    users = mongo.db.users
    existing_user = None

    if data.get("email"):
        existing_user = users.find_one({"email": data["email"]})

    if not existing_user:
        existing_user = users.find_one({
            "oauth_id": data["oauth_id"],
            "provider": data["provider"]
        })

    if not existing_user:
        user_id = users.insert_one(data).inserted_id
        session["user_id"] = str(user_id)
    else:
        users.update_one({"_id": existing_user["_id"]}, {"$set": data})
        session["user_id"] = str(existing_user["_id"])

    session["username"] = data["username"]
    session["avatar"] = data["avatar_url"]

    return redirect(url_for("dashboard.dashboard"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))