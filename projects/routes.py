from flask import render_template, session, redirect, url_for, request
from bson.objectid import ObjectId
from datetime import datetime
import json
import google.generativeai as genai


from extensions import mongo
from . import projects_bp

@projects_bp.route("/clients/<client_id>/projects", methods=["GET", "POST"])
def client_projects(client_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    client = mongo.db.clients.find_one({
        "_id": ObjectId(client_id),
        "user_id": session["user_id"]
    })

    if not client:
        return redirect(url_for("clients.clients"))

    if request.method == "POST":
        deadline_raw = request.form.get("deadline")
        deadline = datetime.fromisoformat(deadline_raw) if deadline_raw else None

        use_ai = request.form.get("use_ai") == "on"

        project_id = mongo.db.projects.insert_one({
            "user_id": session["user_id"],
            "client_id": ObjectId(client_id),
            "client_name": client["name"],
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "status": "Planning",
            "deadline": deadline,
            "created_at": datetime.utcnow()
        }).inserted_id

        if use_ai:
            generate_tasks(
                project_id=project_id,
                description=request.form.get("description"),
                user_id=session["user_id"]
            )

        return redirect(url_for("projects.project_detail", project_id=project_id))


    projects = mongo.db.projects.find({
        "user_id": session["user_id"],
        "client_id": ObjectId(client_id)
    })

    return render_template(
        "projects.html",
        projects=projects,
        client=client
    )
@projects_bp.route("/projects/<project_id>")
def project_detail(project_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    project = mongo.db.projects.find_one({
        "_id": ObjectId(project_id),
        "user_id": session["user_id"]
    })

    if not project:
        return redirect(url_for("dashboard.dashboard"))

    tasks = mongo.db.tasks.find({
        "project_id": project["_id"],
        "user_id": session["user_id"]
    }).sort("status", -1)

    total_tasks = mongo.db.tasks.count_documents({
        "project_id": project["_id"],
        "user_id": session["user_id"]
    })

    done_tasks = mongo.db.tasks.count_documents({
        "project_id": project["_id"],
        "user_id": session["user_id"],
        "status": "Done"
    })

    progress = int((done_tasks / total_tasks) * 100) if total_tasks else 0

    return render_template(
        "project_detail.html",
        project=project,
        tasks=tasks,
        progress=progress,
        total_tasks=total_tasks,
        done_tasks=done_tasks
    )
@projects_bp.route("/projects/<project_id>/tasks/add", methods=["POST"])
def add_task(project_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    mongo.db.tasks.insert_one({
        "user_id": session["user_id"],
        "project_id": ObjectId(project_id),
        "description": request.form.get("description"),
        "hours": float(request.form.get("hours", 0)),
        "status": "Pending",
        "created_at": datetime.utcnow()
    })

    return redirect(url_for("projects.project_detail", project_id=project_id))

@projects_bp.route("/tasks/<task_id>/toggle")
def toggle_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    task = mongo.db.tasks.find_one({
        "_id": ObjectId(task_id),
        "user_id": session["user_id"]
    })

    if not task:
        return redirect(url_for("dashboard.dashboard"))

    new_status = "Done" if task["status"] == "Pending" else "Pending"

    mongo.db.tasks.update_one(
        {"_id": task["_id"]},
        {"$set": {"status": new_status}}
    )

    return redirect(url_for(
        "projects.project_detail",
        project_id=task["project_id"]
    ))

@projects_bp.route("/tasks/<task_id>/edit", methods=["POST"])
def edit_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    task = mongo.db.tasks.find_one({
        "_id": ObjectId(task_id),
        "user_id": session["user_id"]
    })

    if not task:
        return redirect(url_for("dashboard.dashboard"))

    mongo.db.tasks.update_one(
        {"_id": task["_id"]},
        {"$set": {
            "description": request.form.get("description"),
            "hours": float(request.form.get("hours", 0))
        }}
    )

    return redirect(url_for(
        "projects.project_detail",
        project_id=task["project_id"]
    ))

@projects_bp.route("/tasks/<task_id>/delete")
def delete_task(task_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    task = mongo.db.tasks.find_one({
        "_id": ObjectId(task_id),
        "user_id": session["user_id"]
    })

    if task:
        mongo.db.tasks.delete_one({"_id": task["_id"]})

    return redirect(url_for(
        "projects.project_detail",
        project_id=task["project_id"]
    ))

@projects_bp.route("/projects/<project_id>/complete")
def complete_project(project_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    project = mongo.db.projects.find_one({
        "_id": ObjectId(project_id),
        "user_id": session["user_id"]
    })

    if not project:
        return redirect(url_for("dashboard.dashboard"))

    mongo.db.projects.update_one(
        {"_id": project["_id"]},
        {"$set": {"status": "Completed"}}
    )

    return redirect(url_for(
        "invoices.invoices",
        prefill_client=project["client_name"],
        prefill_project=project["title"]
    ))

@projects_bp.route("/projects/<project_id>/delete")
def delete_project(project_id):
    if "user_id" not in session:
        return redirect(url_for("auth.index"))

    project = mongo.db.projects.find_one({
        "_id": ObjectId(project_id),
        "user_id": session["user_id"]
    })

    if project:
        # delete tasks first
        mongo.db.tasks.delete_many({
            "project_id": project["_id"],
            "user_id": session["user_id"]
        })

        # delete project
        mongo.db.projects.delete_one({
            "_id": project["_id"]
        })

    return redirect(url_for(
        "projects.client_projects",
        client_id=project["client_id"]
    ))

def generate_tasks(project_id, description, user_id):
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Break this project into an appropriate number of concrete technical tasks.
    Rules:
    - Tasks should be on point and linited to atmost 15 
    - Return ONLY valid JSON
    - No text outside JSON
    - Format:
    [
      {{ "task": "Task description", "hours": 2 }}
    ]

    Project description:
    {description}
    """

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        start = text.find("[")
        end = text.rfind("]")

        if start == -1 or end == -1:
            return

        tasks = json.loads(text[start:end + 1])

        for t in tasks:
            mongo.db.tasks.insert_one({
                "user_id": user_id,
                "project_id": project_id,
                "description": t.get("task"),
                "hours": float(t.get("hours", 1)),
                "status": "Pending",
                "created_at": datetime.utcnow()
            })

    except Exception as e:
        print("AI ERROR:", e)
