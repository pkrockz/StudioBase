from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from datetime import datetime

from extensions import mongo, oauth
from . import auth_bp


# ---------- Helpers ----------

def oauth_error(message):
    return render_template("login.html", error=message)


# ---------- Routes ----------

@auth_bp.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html")


@auth_bp.route("/login/github")
def login_github():
    github = oauth.create_client("github")
    redirect_uri = url_for("auth.authorize_github", _external=True)
    return github.authorize_redirect(redirect_uri)


@auth_bp.route("/login/google")
def login_google():
    google = oauth.create_client("google")
    redirect_uri = url_for("auth.authorize_google", _external=True)
    return google.authorize_redirect(redirect_uri)


# ---------- OAuth Callbacks ----------

@auth_bp.route("/authorize/github")
def authorize_github():
    github = oauth.create_client("github")

    try:
        token = github.authorize_access_token()
    except Exception:
        return oauth_error("GitHub login was cancelled or failed.")

    if not token:
        return oauth_error("GitHub authentication failed.")

    user_info = github.get("user", token=token).json()

    if not user_info or "id" not in user_info:
        return oauth_error("Could not retrieve GitHub user information.")

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
    google = oauth.create_client("google")

    try:
        token = google.authorize_access_token()
    except Exception:
        return oauth_error("Google login was cancelled or failed.")

    if not token:
        return oauth_error("Google authentication failed.")

    user_info = token.get("userinfo")

    if not user_info or "sub" not in user_info:
        return oauth_error("Could not retrieve Google user information.")

    user_data = {
        "oauth_id": user_info["sub"],
        "provider": "google",
        "username": user_info["name"],
        "email": user_info["email"],
        "avatar_url": user_info["picture"],
    }

    return handle_login(user_data)


# ---------- Login Handler ----------

def handle_login(data):
    if not data or not data.get("oauth_id"):
        return oauth_error("Invalid login data received.")

    try:
        users = mongo.db.users
    except Exception:
        return oauth_error("Database connection error. Please try again.")

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


# ---------- Logout ----------

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))

#Delete
@auth_bp.route("/delete-account", methods=["GET"])
def delete_account_confirm():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    return render_template("delete_account.html")

@auth_bp.route("/delete-account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]

    # Delete in correct order
    mongo.db.tasks.delete_many({"user_id": user_id})
    mongo.db.projects.delete_many({"user_id": user_id})
    mongo.db.clients.delete_many({"user_id": user_id})
    mongo.db.invoices.delete_many({"user_id": user_id})
    mongo.db.users.delete_one({"_id": ObjectId(user_id)})

    session.clear()
    return redirect(url_for("auth.index"))

# ---------- Global Safety Net ----------

@auth_bp.errorhandler(Exception)
def auth_error_handler(e):
    return oauth_error("Authentication failed. Please try again.")
