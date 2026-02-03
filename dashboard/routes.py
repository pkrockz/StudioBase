from flask import render_template, session, redirect, url_for
from datetime import datetime
from bson.objectid import ObjectId

from extensions import mongo
from . import dashboard_bp


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    user_id = session["user_id"]
    today_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Active Projects Count
    active_projects_count = mongo.db.projects.count_documents({
        "user_id": user_id,
        "status": {"$ne": "Completed"}
    })

    # 2. Pipeline Value
    pipeline_cursor = mongo.db.prospects.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total": {"$sum": "$value"}}}
    ])
    pipeline_val = list(pipeline_cursor)
    pipeline_total = pipeline_val[0]["total"] if pipeline_val else 0

    # 3. Pending Tasks
    pending_tasks_count = mongo.db.tasks.count_documents({
        "user_id": user_id,
        "status": "Pending"
    })

    # 4. Overdue Invoices
    overdue_count = mongo.db.invoices.count_documents({
        "user_id": user_id,
        "status": "Unpaid",
        "due_date": {"$lt": today_str}
    })

    # 5. Urgent Leads
    urgent_leads = mongo.db.leads.find({
        "user_id": user_id,
        "status": "Cold"
    }).sort("created_at", 1).limit(5)

    # 6. Active Projects + Progress
    projects_cursor = mongo.db.projects.find({
        "user_id": user_id,
        "status": {"$ne": "Completed"}
    }).sort("deadline", 1).limit(5)

    active_projects = []
    for p in projects_cursor:
        total_tasks = mongo.db.tasks.count_documents({"project_id": p["_id"]})
        done_tasks = mongo.db.tasks.count_documents({
            "project_id": p["_id"],
            "status": "Done"
        })

        progress = int((done_tasks / total_tasks) * 100) if total_tasks > 0 else 0

        p["progress"] = progress
        p["tasks_done"] = done_tasks
        p["tasks_total"] = total_tasks
        active_projects.append(p)

    return render_template(
        "dashboard.html",
        username=session.get("username"),
        active_projects_count=active_projects_count,
        pipeline_total=pipeline_total,
        pending_tasks_count=pending_tasks_count,
        overdue_count=overdue_count,
        urgent_leads=urgent_leads,
        active_projects=active_projects,
    )